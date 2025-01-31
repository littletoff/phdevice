import datetime
import plotly.graph_objects as go
import requests
from nicegui import ui
import os
import uvicorn

# Global variables
x = 0
ph_value = 7.0  # Default pH value
water_quality = ""  # Empty string, default UI water quality text
water_quality_2 = ""
text_color = "#000000" 
tbm = 1  # Time between data updates in seconds
max_measurements = 20  # Maximum number of depicted measurements in the graph
ph_values_list = []  # List of pH values for graph
timestamps_list = []  # List of corresponding timestamps
# Offsets
offset = 0.00
offset_1 = 0.00
offset_2 = 0.00

# ThingSpeak Information
channel_id = "2705567"  # ThingSpeak channel ID
read_api_key = "8WH3F7FD76QJZ9GA"  # Read API Key
write_api_key = "0J5VZSYZSS0Y62HC"  # Write API Key
write_api_key_2 = "Z75KEEOSME6QSARG"  # Write API Key for bypassing cooldown
read_url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"  # ThingSpeak read channel URL
request_params = {
    "api_key": read_api_key,  # Read API Key
    "results": 1  # Number of data points to retrieve
}

# ThingSpeak request function
def request_data(field_number):
    response = requests.get(read_url, request_params)  # Send HTTP GET request
    if response.status_code == 200:  # 200 = success
        data = response.json()
        feeds = data.get("feeds", [])  # Extract "feeds" from JSON data
        if feeds:  # Check if feeds list is not empty
            latest_ph_value = round(float(feeds[0].get(f"field{field_number}")), 2)
            return latest_ph_value  # Return rounded pH data
    return None  # Return None if request fails

# ThingSpeak send function
def send_data(value, field_number):
    url = "https://api.thingspeak.com/update"  # ThingSpeak update URL
    print(f"Sending {field_number}: {value}")
    payload = {
        "api_key": write_api_key,  # Write API Key
        f"field{field_number}": value  # Field and corresponding data
    }
    response = requests.post(url, data=payload)  # Send data
    return response.status_code == 200  # Check for success

def send_string_data(message, api_key):
    url = "https://api.thingspeak.com/update"  # ThingSpeak update URL
    print(f"Sending {message}: {api_key}")
    payload = {
        "api_key": api_key,  # Write API Key
        "status": message,  # String data
    }
    response = requests.post(url, data=payload)  # Send data
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    return response.status_code == 200  # Check for success

# Function to update both UI and graph
def update_ui():
    global ph_value, timestamps_list, ph_values_list, x
    # Get current time and data from ThingSpeak
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    new_ph_value = request_data(1)

    if new_ph_value is not None:
        ph_value = new_ph_value # Change pH Data with lates pH data
    # Change text and text colour depending on pH level
    if ph_value < 7.2: 
        water_quality = "WARNING! Your pool water is too acidic!"
        water_quality_2 = "(pH < 7.2)"
        text_color = "#e00b0b"
    elif ph_value > 7.8:
        water_quality = "WARNING! Your pool water is too alkaline!"
        water_quality_2 = "(ph > 7.8)"
        text_color = "#e00b0b"
    else:
        water_quality = "Your pool water is fine."
        water_quality_2 = "(pH 7.2 - 7.8)"
        text_color = "#000000"
    
    ph_label.text = f"{ph_value}"
    clock_label.text = f"{current_time}"
    water_quality_label_1.text = f"{water_quality}"
    water_quality_label_2.text = f"{water_quality_2}"
    water_quality_label_1.style(f"color:{text_color}")
    water_quality_label_2.style(f"color:{text_color}")
    
    # Update graph with new pH value and timestamp every tbm seconds
    x += 1 # goes up by 1 every time update_ui is called
    if x == tbm: # if x is the same as tbm the graph is updated
        x = 0 # resets x
        # Update Graph
        timestamps_list.append(current_time)
        ph_values_list.append(ph_value)
        # Limit the number of measurement points on the graph
        if len(timestamps_list) > max_measurements:
            timestamps_list = timestamps_list[-max_measurements:]
            ph_values_list = ph_values_list[-max_measurements:]
        # Changes the graph to display new list of information
        fig.data[0].x = timestamps_list
        fig.data[0].y = ph_values_list

        plot.update()  # Updates the graph

def update_max_measurements(new_max_measurements):
    global max_measurements
    max_measurements = new_max_measurements # Updates the amount of max measurements in the graph globally
    return max_measurements

def update_tbm(new_tbm):
    global tbm
    tbm = float(new_tbm) # Updates the time between measurements in the graph globally
    return tbm
    
# Change Font
ui.add_head_html('''<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap" rel="stylesheet"><style>body {font-family: 'Source Sans Pro', sans-serif; font-weight: 600;}</style>''')
    
# NETWORK ADD Page
@ui.page("/network_add")
def network_add():
    ui.button("back", on_click=lambda: ui.navigate.back()).props("icon=arrow_back") # Back arrow
    with ui.card().style("position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);") as network_card: # Card, what you see in the screen
        ssid_input = ui.input("Network SSID") # Inputs
        password_input = ui.input("Network Password")
        with ui.row().classes("justify-stretch"): # Style
            # Done Button
            network_done_button = ui.button("Confirm", on_click=lambda: (network_done_button.disable(), update_ssid_pass(ssid_input.value, password_input.value))).props('icon=check')
# Function to update network information globally
def update_ssid_pass(new_ssid, new_pass): 
    global write_api_key, write_api_key_2
    ui.notify(f"Network has been added. SSID: {new_ssid}, Password: {new_pass}", type='positive') # Send notification
    print(new_ssid, new_pass)
    send_string_data(new_ssid, write_api_key)
    send_string_data(new_pass, write_api_key_2)
    
# Function to calculate the offset, that will be spent to the Arduino
def calculate_offset():
    global offset_1, offset_2
    offset = round(16.56 + ((offset_1 + offset_2) / 2), 2) # Take the average of offset 1 and 2 and round it to 2 decimal points
    print("offsets:", offset_1, offset_2, offset)
    ui.notify(f"Recalibration complete. New offset = {offset}. You may now return to the home page.", type="positive") # Notify end
    send_data(offset, 1) # Calls function to send offset data
    
# Called when first step on stepper is complete, calculates offset 1
def step_one():
    global ph_value, stepper
    print("one")
    offset_1 = round(4.0 - ph_value, 2) # Calculates offset 1 and rounds it
    print("step one:", ph_value, offset_1)
    ui.notify(f"First offset = {offset_1}", color="primary", type="info") # Notify user of first offset
    with stepper:
        stepper.next() # Next step
        
# Called when second step of stepper is complete, calculates offset 2
def step_two():
    global ph_value, offset_2, stepper, offset_2_label
    offset_2 = round(7.0 - ph_value, 2) # Calculates offset 2 and rounds it
    print("step two:", ph_value, offset_2)
    ui.notify(f"Second offset = {offset_2}", color="primary", type="info") # Notify user of second offset
    with stepper:
        stepper.next() # Next step

# Recalibration page
@ui.page("/recalibration")
def recalibration():
    global stepper
    ui.button("back", on_click=lambda: ui.navigate.back()).props("icon=arrow_back") # Back button
    with ui.column().classes("border p-6").style("position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"): # Styling
        with ui.stepper().props("vertical").classes("w-full") as stepper: # Stepper
            # First step of Stepper with label and Next button, which calls function
            with ui.step('Step One'):
                ui.label('Hold pH-Meter in pH 4.00 Solution until stable')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=lambda: step_one())
            # Second step of Stepper with label, next button and back button. Next button calls function
            with ui.step('Step Two'):
                ui.label('Hold pH-Meter in pH 7.00 Solution until stable')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=lambda: step_two())
                    ui.button('Back', on_click=stepper.previous).props('flat')
            # Final step of Stepper with label, done button and back button. Done button calls function to end Recalibration process
            with ui.step('Step Three'):
                ui.label('Confirm finalization of recalibration')
                with ui.stepper_navigation():
                    done_button = ui.button('Done', on_click=lambda: (calculate_offset(), done_button.disable()))
                    ui.button('Back', on_click=stepper.previous).props('flat')

# UI Layout Setup
ui.page_title("pH-measurements Web App") # Title, doesn't do much when hosted on a server but is nice for private hosting
# Styling
with ui.column().classes("border p-6").style("position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"):
    with ui.column(): # Columns for Positioning
        with ui.grid(columns=2):
            with ui.grid(columns=1):
                # pH Value and Time in top left
                with ui.grid(columns=2).classes("border p-4"):
                    ui.label("pH-Value:")
                    ph_label = ui.label(str(ph_value))

                    ui.label("Time:")
                    clock_label = ui.label("")
                # "Warning" Labels below the data, changes dynamically at different pH levels
                with ui.row().classes("justify-center"):
                    water_quality_label_1 = ui.label("")
                with ui.row().classes("justify-center"): # Second line for stylistic reasons
                    water_quality_label_2 = ui.label("")
                    
            # Q-Fabs top right which open buttons -> lead to other pages
            with ui.grid(columns=2):
                with ui.grid(rows=2):
                    with ui.element('q-fab').props('icon=wifi color=blue flat'): # Flat inverts the button colours 
                        ui.button("Add New Network", on_click=lambda: ui.navigate.to("/network_add")).props("rounded") # Network page
                    with ui.element('q-fab').props('icon=edit color=blue flat'):
                        ui.button("Recalibrate pH-Meter", on_click=lambda: ui.navigate.to("/recalibration")).props("rounded") # Recalibration page
                        
        # Slider for max measurements and number input for time between measurements UI
        with ui.grid(rows=2).classes("border p-4"): # Positioning
            with ui.grid(columns=1).classes("border p-4"):
                slider_1 = ui.slider(min=0, max=100, value=max_measurements) # Slider, min=0 max=100
                # Slider text
                with ui.grid(columns=2):
                    ui.label("Amount of Displayed Measurements:")
                    # Trigger function with inputted value
                    ui.label().bind_text_from(slider_1, "value", update_max_measurements)

            with ui.grid(columns=1).classes("border p-4"):
                tbm_select = ui.number(label="Seconds between Measurements:", value=tbm, format="%.2f", on_change=lambda: update_tbm(tbm_select.value))

        fig = go.Figure() # Initialize Graph
        fig.add_trace(go.Scatter(x=[], y=[], mode="lines+markers", name="pH Value")) # Scatter Graph, mode, name
        fig.update_layout(xaxis_title="Time of Measurement", yaxis_title="pH-Value", margin=dict(l=0, r=0, t=0, b=0)) #Axis titles
        plot = ui.plotly(fig).classes("w-full h-40") # Render the initial graph

ui.timer(tbm, update_ui)

# Use Uvicorn to run the app for Heroku compatibility
if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 5000))  # Convert port to an integer
    ui.run(native=False, port=port)  # Run the app in server mode (not native)
