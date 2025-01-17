import datetime
import plotly.graph_objects as go
import requests
from nicegui import ui
from nicegui.elements import stepper

# global variables
x = 0
ph_value = 7.0  # default ph value
water_quality = ""  # empty string, default UI water quality text
water_quality_2 = ""
text_color = "#000000"
tbm = 1  # Time between data updates in seconds
max_measurements = 20  # maximum amount of depicted measurements in the graph
ph_values_list = []  # List of pH Values for graph
timestamps_list = []  # List of corresponding timestamps
# offsets
offset = 0.00
offset_1 = 0.00
offset_2 = 0.00

# ThingSpeak Information
channel_id = "2705567" # ThingSpeak channel ID
read_api_key = "8WH3F7FD76QJZ9GA" # Read API Key (for
write_api_key = "0J5VZSYZSS0Y62HC" # Write API Key (for SSID and Recal.)
write_api_key_2 = "Z75KEEOSME6QSARG" #Write API Key (for passwords to bypass 15s cooldown)
read_url = f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"  # ThingSpeak read channel URL
request_params = {
    "api_key": read_api_key,  # Read API Key
    "results": 1  # Number of data points to retrieve
}

# ThingSpeak request function
def request_data(field_number):
    response = requests.get(read_url, request_params) # send HTTP-get request with specified Information
    if response.status_code == 200: # 200 = success
        # Parse JSON data
        data = response.json()
        feeds = data.get("feeds", []) # extract the "feeds" list from json data
        if feeds: # check if feeds list is not empty
            # Get the latest pH value and round it to 2 decimal points
            latest_ph_value = round(float(feeds[0].get(f"field{field_number}")), 2)
            return latest_ph_value #return rounded pH data
    return None # return None if request fails

# ThingSpeak send function
def send_data(value, field_number): # function to send value
    url = "https://api.thingspeak.com/update" # ThingSpeak update URL
    print(f"Sending {field_number}: {value}")
    payload = { # data to be sent
        "api_key": write_api_key, # write API Key
        f"field{field_number}": value # field and corresponding data
    }
    response = requests.post(url, data=payload) # sends data
    return response.status_code == 200 # check for success

def send_string_data(message, api_key): # Function to send strings
    url = "https://api.thingspeak.com/update" # ThingSpeak update URL
    print(f"Sending {message}: {api_key}")
    payload = { # data to be sent
        "api_key": api_key, # specified write API Key
        "status": message, # String data sent to status -> no field number necessary
    }
    response = requests.post(url, data=payload) # sends data
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    return response.status_code == 200 # check for success

# Function to update both UI and graph
def update_ui():
    global ph_value, timestamps_list, ph_values_list, x
    # Get current time and pH value from ThingSpeak
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    new_ph_value = request_data(1)

    if new_ph_value is not None:
        ph_value = new_ph_value  # Update the global pH value

    # Change water_quality depending on ph_value to then show in the UI
    if ph_value < 7.2:
        water_quality = "WARNING! Your pool water is too acidic!"
        water_quality_2 = "(pH < 7.2)"
        text_color = "#e00b0b"  #red
    elif ph_value > 7.8:
        water_quality = "WARNING! Your pool water is too alkaline!"
        water_quality_2 = "(ph > 7.8)"
        text_color = "#e00b0b"  #red
    else:
        water_quality = "Your pool water is fine."
        water_quality_2 = "(pH 7.2 - 7.8) "
        text_color = "#000000"  #black

    # Updates pH, time, water quality text and water quality text color in the UI
    ph_label.text = f"{ph_value}"
    clock_label.text = f"{current_time}"
    water_quality_label_1.text = f"{water_quality}"
    water_quality_label_2.text = f"{water_quality_2}"
    water_quality_label_1.style(f"color:{text_color}")
    water_quality_label_2.style(f"color:{text_color}")

    # Update graph with new pH value and timestamp every tbm seconds
    x += 1  # goes up by 1 every time update_ui is called
    if x == tbm:  # if x is the same as tbm the graph is updated
        x = 0  # resets x
        timestamps_list.append(current_time)
        ph_values_list.append(ph_value)

        # Limit the number of measurement points on the graph
        if len(timestamps_list) > max_measurements:
            timestamps_list = timestamps_list[-max_measurements:]
            ph_values_list = ph_values_list[-max_measurements:]

        # Changes the graph to display new list of information
        fig.data[0].x = timestamps_list
        fig.data[0].y = ph_values_list

        plot.update()  # updates the graph


def update_max_measurements(new_max_measurements): # Function to update Maximum amount of measurements plotted in Graph
    global max_measurements
    max_measurements = new_max_measurements # updates Max measurements
    return max_measurements

def update_tbm(new_tbm): # Function to update TBM
    global tbm
    tbm = float(new_tbm) # updates tbm
    return tbm
# Font
ui.add_head_html('''
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
    body {
        font-family: 'Source Sans Pro', sans-serif;
        font-weight: 600; /* Set to a heavier weight */
    }
</style>
''')

# NETWORK ADD
@ui.page("/network_add") # New page: Network Add
def network_add():
    ui.button("back", on_click=lambda: ui.navigate.back()).props("icon=arrow_back") # Back button
    with ui.card().style("position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);") as network_card: # Initialize card
        # SSID and Password inputs
        ssid_input = ui.input("Network SSID")
        password_input = ui.input("Network Password")
        # confirm button -> calls function to update ssid and password
        with ui.row().classes("justify-stretch"):
            network_done_button = ui.button("Confirm", on_click=lambda: (network_done_button.disable(), update_ssid_pass(ssid_input.value, password_input.value))).props('icon=check')

def update_ssid_pass(new_ssid, new_pass):
    global write_api_key, write_api_key_2
    ui.notify(f"Network has been added. SSID: {new_ssid}, Password: {new_pass}", type='positive')
    print(new_ssid, new_pass)
    send_string_data(new_ssid, write_api_key)
    send_string_data(new_pass, write_api_key_2)


## OFFSET ##
# Function to calculate offset
def calculate_offset():
    global offset_1, offset_2
    offset = round(16.56 + ((offset_1 + offset_2) / 2), 2) # Offset calculated as average between measured offsets + default offset
    print("offsets:", offset_1, offset_2, offset) # prints offsets to console
    ui.notify(f"Recalibration complete. New offset = {offset}. You may now return to the home page.",
              type="positive")  # Notification UI
    send_data(offset, 1) # Call function to send data to ThingSpeak

def step_one(): # Called when first step of Recal. is done
    global ph_value, stepper
    print("one")
    offset_1 = round(4.0 - ph_value, 2) # Calculates offset 1
    print("step one:", ph_value, offset_1)
    ui.notify(f"First offset = {offset_1}", color="primary", type="info")
    with stepper:
        stepper.next() # Next step

def step_two(): # Called when second step of Recal. is done
    global ph_value, offset_2, stepper, offset_2_label
    offset_2 = round(7.0 - ph_value, 2) # Calculates offset 2
    print("step two:", ph_value, offset_2)
    ui.notify(f"Second offset = {offset_2}", color="primary", type="info")
    with stepper:
        stepper.next() # Next step

# RECALIBRATION
@ui.page("/recalibration") # New page: Recalibration
def recalibration():
    global stepper
    ui.button("back", on_click= lambda: ui.navigate.back()).props("icon=arrow_back") # Back button
    with ui.column().classes("border p-6") \
            .style("position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"):  # positions everything centrally
        with ui.stepper().props("vertical").classes("w-full") as stepper: # Stepper
            with ui.step('Step One'):
                ui.label('Hold pH-Meter in pH 4.00 Solution until stable')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=lambda: step_one()) # Calls step_one when pressed
            with ui.step('Step Two'):
                ui.label('Hold pH-Meter in pH 7.00 Solution until stable')
                with ui.stepper_navigation():
                    ui.button('Next', on_click=lambda: step_two()) # Calls step_two when pressed
                    ui.button('Back', on_click=stepper.previous).props('flat') # go back
            with ui.step('Step Three'):
                ui.label('Confirm finalization of recalibration')
                with ui.stepper_navigation():
                    # Done button: calls function to calculate offset
                    done_button = ui.button('Done', on_click=lambda: (calculate_offset(), done_button.disable() ))
                    ui.button('Back', on_click=stepper.previous).props('flat') # go back

# UI Layout Setup
ui.page_title("pH-measurements Web App")  #page title

with ui.column().classes("border p-6") \
        .style("position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);"):  # positions everything centrally
    with ui.column(): # aligns everything
        with ui.grid(columns=2):  #aligns labels with buttons
            with ui.grid(columns=1):  #aligns top labels-box with water_quality labels
                with ui.grid(columns=2).classes("border p-4"):
                    # pH Value and Time UI:
                    ui.label("pH-Value:")
                    ph_label = ui.label(str(ph_value))

                    ui.label("Time:")
                    clock_label = ui.label("")

                with ui.row().classes("justify-center"):
                    water_quality_label_1 = ui.label("")  # Water Quality text UI ("Warning" etc)
                with ui.row().classes("justify-center"):
                    water_quality_label_2 = ui.label("")  # Water Quality text UI (pH = xx)

            with ui.grid(columns=2): #halves the size of the q-fabs, empty column two, space for buttons
                with ui.grid(rows=2): #aligns q-fabs
                    with ui.element('q-fab').props('icon=wifi color=blue flat'): # Add New Network q-fab and button
                        ui.button("Add New Network", on_click=lambda: ui.navigate.to("/network_add")).props("rounded")  #calls network_add func
                    with ui.element('q-fab').props('icon=edit color=blue flat'):  # Recalibrate q-fab and button
                        ui.button("Recalibrate pH-Meter", on_click=lambda: ui.navigate.to("/recalibration")).props("rounded")  # calls recalibration func

        # Slider for max measurements and number input for time between measurements UI
        with ui.grid(rows=2).classes("border p-4"): # Positioning
            with ui.grid(columns=1).classes("border p-4"):
                slider_1 = ui.slider(min=0, max=100, value=max_measurements) # Slider
                # Slider text
                with ui.grid(columns=2):
                    ui.label("Amount of Displayed Measurements:")
                    # Trigger Function with inputted value
                    ui.label().bind_text_from(slider_1, "value", update_max_measurements)

            with ui.grid(columns=1).classes("border p-4"):
                tbm_select = ui.number(label="Seconds between Measurements:", value=tbm, format="%.2f",
                                       on_change=lambda: update_tbm(tbm_select.value)) # Changes Text

        # Graph
        fig = go.Figure() # Initialize Graph
        fig.add_trace(go.Scatter(x=[], y=[], mode="lines+markers", name="pH Value"))  # Lists for x and y, mode, title
        fig.update_layout(xaxis_title="Time of Measurement", yaxis_title="pH-Value", margin=dict(l=0, r=0, t=0, b=0)) #Axis titles
        plot = ui.plotly(fig).classes("w-full h-40")  # Render the initial graph

# Set up the timer to update UI every second
ui.timer(tbm, update_ui)
# Run the application
ui.run()
