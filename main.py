# Wireless Communication using Access Point Mode of RPi Pico W

# Libraries
# libraries for wireless communication part
import network
import socket
# libraries for sensor circuit part
import machine 
import utime # time library could be used instead
import math # library to perform mathematical operations

# Configure GP14 as an output pin. An actuator (red LED) is connected to this pin.
#led = machine.Pin(14, machine.Pin.OUT)

# Configure ADC(1), which is GP27, as ADC channel and call it as temp_sensor
temp_sensor = machine.ADC(0)
light_reciever = machine.ADC(1)


red_led = machine.Pin(15, machine.Pin.OUT)
green_led = machine.Pin(14, machine.Pin.OUT)


# define a function to get the status of light sensor
def get_tempSensorValue():
    tempSensorValue = temp_sensor.read_u16() # read the ADC output and store it
# The below equation gives temperature in degree Celcius. Adjust the value 10 in the denominator to calibrate the sensor reading. 
    tempValue = round(((((1/(1/298+(1/3960)*math.log((65535/(tempSensorValue)-1)))) - 273)*10)/7.5),1)
    return str(tempValue)
def web_page2(tempValue,colour):
    html = f""" 
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 200px; }}
            #temp {{
                font-size: 200px;
                font-weight: bold;
                filter: brightness(100%);
                
                color: {colour};  /* Set initial color based on current status */
            }}
        
        </style>
        <script>
            function updateTemp() {{
                fetch('/temp')  // Request the latest temperature value
                .then(response => response.text())  // Convert response to text
                .then(data => {{
                    const [temp, color,bg_color] = data.split(",");  // Receive temp, colour,bg_color
                    const tempElement = document.getElementById("temp");
                    tempElement.innerText = temp + " C";  // Update temperature display
                    tempElement.style.color = color;  // Update color based on the temperature status
                    document.body.style.backgroundColor = bg_color;
                }});
            }}

            setInterval(updateTemp, 1000);  // Update temperature every second
        </script>
        <script>
            function sendValue(inputName, value) {{
                fetch("/" + inputName + "?value=" + encodeURIComponent(value))
                    .then(response => console.log("Sent: " + inputName + " = " + value))
                    .catch(error => console.error("Error:", error));
            }}
        </script>
    </head>
    <body>
        <p> <span id="temp">{tempValue} C</span></p>
        <h2>Enter Minimum Value:</h2>
        <input type="number" oninput="sendValue('input1', this.value)" placeholder="Minimum input..." />

        <h2>Enter Maximum Value:</h2>
        <input type="number" oninput="sendValue('input2', this.value)" placeholder="Minimum input..." />

    </body>
    </html>
    """
    
    return html

# Create an Access Point
ssid = 'QuinnCooper'       #Set access point name. you can change this. 
password = '12345678'      #Set your access point password. you can use your own password.

ap = network.WLAN(network.AP_IF)
ap.config(essid=ssid, password=password)
ap.active(True)            #activating

while ap.active() == False:
  pass
print('Connection is successful')
print(ap.ifconfig()) # get the ip address of the Pico W. This info will be used to connect to the Pico. 


# Create a socket server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

# Response when connection received

minimum = 26
maximum = 34

colour = "green"

dim_mode = False
# code for ambient light sensor, dim interface function activates when exceeding 63000
light_threshold = 63000
sensing_light = False
is_dim = False

# colors used in user interface
GREEN_NORMAL = "green"
RED_NORMAL = "red"
GREEN_DIM = "seagreen"
RED_DIM = "firebrick"
BG_DIM = "lightgray"
BG_NORMAL = "white"
bg_colour = BG_NORMAL

time = 0
light_reading = 0
tempValue = 0
while True:
    conn, addr = s.accept()
    request = conn.recv(1024).decode()  # Decode the request
    
    
    time+=1
    utime.sleep(1)
    light_reading = light_reciever.read_u16()
    print(f"\n----Time = {time}s----")
    print("Is Dim:",is_dim)
    print(f"Temp: {tempValue}C")
    print(f"Range: {minimum}C - {maximum}C")
    print(f"Colour: {colour}")
    
    
    #Dim only gets toggled when there stops being light
    if (sensing_light == False):
        if(light_reading > light_threshold):
            sensing_light = True
            print("dim toggled")
            if is_dim:
                is_dim = False
                bg_colour = BG_NORMAL
            else:
                is_dim = True
                bg_colour = BG_DIM
    elif(light_reading < light_threshold):
        sensing_light = False
    
    if  colour == "green":
        green_led.value(1)
        red_led.value(0)
    else:
        green_led.value(0)
        red_led.value(1)
    
    if "GET /input1?" in request:
        value1 = request.split("GET /input1?value=")[-1].split(" ")[0]
        value1 = value1.replace("%20", " ")  # Convert spaces
        print(f"Received minmum: {value1}")
        try:
            minimum = float(value1);
        except:
            print("incorrect min value")
    elif "GET /input2?" in request:
        value2 = request.split("GET /input2?value=")[-1].split(" ")[0]
        value2 = value2.replace("%20", " ")  # Convert spaces
        print(f"Received maximum: {value2}")
        try:
            maximum = float(value2);
        except:
            print("incorrect max value")
    tempValue = get_tempSensorValue()

    #detect green and red use for led and user interface
    if (float(tempValue) < minimum or float(tempValue)> maximum):
        colour = "red"
    else:
        colour = "green"
    if "GET /temp" in request:#html script runs this once a second
        
        
        if is_dim:
            if colour == "green":
                response = f"{tempValue},{GREEN_DIM},{bg_colour}"
            else:
                response = f"{tempValue},{RED_DIM},{bg_colour}"
        else:
            if colour == "green":
                response = f"{tempValue},{GREEN_NORMAL},{bg_colour}"
            else:
                response = f"{tempValue},{RED_NORMAL},{bg_colour}"
        conn.send("HTTP/1.1 200 OK\n")
        conn.send("Content-Type: text/plain\n")
        conn.send("Connection: close\n\n")
        conn.sendall(response)

    else:
        # Send the full HTML page
        tempValue = get_tempSensorValue()
        response = web_page2(tempValue,colour)
        conn.send("HTTP/1.1 200 OK\n")
        conn.send("Content-Type: text/html\n")
        conn.send("Connection: close\n\n")
        conn.sendall(response)

    conn.close()



