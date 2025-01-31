// Libraries
#include <LiquidCrystal_I2C.h>
#include <ThingSpeak.h>
#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
#include <vector> // To store SSIDs and passwords

// Global Variables
float ph_pin = A0; // Analog Pin 0 is defined -> pH-module connected to this output
LiquidCrystal_I2C lcd(0x27, 16, 2); // Define 16 by 2 LCD 
WiFiClient client;

// Thingspeak Information
char* writeAPIKey = "WGI97BCW1S82TN65"; // Write API key
char* readAPIKey2 = "XPKLHK5T9G31SYE9"; // Read API key for channel 2
char* readAPIKey3 = "XM5NCK03FCWB4OJN"; // Read API Key for channel 3
const long channelID = 2705567; // ThingSpeak channel ID
const long channelID2 = 2801763; // ThingSpeak channel 2 ID (for offset and SSIDs)
const long channelID3 = 2803519; // ThingSpeak channel 3 ID (for passwords)
const char* server = "api.thingspeak.com";
const int port = 80; // HTTP Request port

HttpClient httpClient(client, server, port);

// Other constants
float offset = 16.46; // default offset from first calibration
String channelStatus = "";

// Vectors to store SSIDs and passwords
std::vector<String> wifiSSIDs = {"adoli-home"}; // Preloaded with the current SSID
std::vector<String> wifiPasswords = {"zugerberg1"}; // Preloaded with the current password

void setup() {

  Serial.begin(9600);
  analogReadResolution(12); // Change ADC Resolution 

  // LCD I2C Display
  lcd.init(); // Initialize LCD
  lcd.backlight(); // Turns on LCD Backlight
  lcd.clear(); // Clears Display of previous text

  // Attempt Wi-Fi connection
  connectToAvailableWiFi();
  Serial.println("Start");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectToAvailableWiFi(); // Retry Wi-Fi connection if disconnected
  }
  
  // MEASUREMENTS AND MATH 
  float sensor_value = analogRead(ph_pin); // Read A0
  float voltage_output = sensor_value * (5.0 / 4095.0); // Convert ADC-value (Analog-to-digital) to voltage output 
  float ph_value = -5.7 * voltage_output + 16.46; // Slope (usually -5.7) x voltage output + offset (determined via buffer solutions)

  // PRINTING in Serial Monitor
  String message = "Voltage Output: " + String(voltage_output) + " | pH: " + String(ph_value) + " | Sensor Value: " + sensor_value;
  Serial.println(message);

  // LCD display
  String message_LCD = "pH: " + String(ph_value); // Set up Message for LCD incl. pH Value
  lcd.setCursor(0, 0); // Sets cursor to first row
  lcd.print(message_LCD); // Prints to LCD

  // Write data to ThingSpeak channel
  writeTSData(channelID, 1, ph_value);
  
  // Read statuses and add to vectors
  readTSStatus(channelID2, wifiSSIDs, readAPIKey2);
  readTSStatus(channelID3, wifiPasswords, readAPIKey3);
  readFieldFromChannel(channelID2, 1, readAPIKey2);

  delay(1000);
}

// ThingSpeak functions
int writeTSData(long TSChannel, unsigned int TSField, float data) { 
  int writeSuccess = ThingSpeak.writeField(TSChannel, TSField, data, writeAPIKey); // Uses ThingSpeak's "writeField" to send data to specified location
  return writeSuccess; // Return the result of the write operation (1 = success, 0 = failure)
}

void readTSStatus(long TSChannel, std::vector<String>& targetVector, const char* readAPI) {
  String url = "http://api.thingspeak.com/channels/" + String(TSChannel) + "/status.json?api_key=" + String(readAPI);

  httpClient.get(url);
  int statusCode = httpClient.responseStatusCode();

  if (statusCode == 200) {
    String response = httpClient.responseBody();
    // Parse the "status" field
    int statusIndex = response.indexOf("\"status\":\"") + 10; // Find "status" field
    int endIndex = response.indexOf("\"", statusIndex);
    String status = response.substring(statusIndex, endIndex);

    // Add the status to the vector if it is not already present
    if (std::find(targetVector.begin(), targetVector.end(), status) == targetVector.end()) {
      targetVector.push_back(status);
    }

    Serial.println("Status added: " + status);
  } else {
    Serial.println("HTTP Error: ");
    Serial.println(statusCode);
  }
}

void readFieldFromChannel(long channelID, int fieldNumber, const char* readAPI) {
  String url = "http://api.thingspeak.com/channels/" + String(channelID) + "/fields/" + String(fieldNumber) + ".json?api_key=" + String(readAPI);
  
  // Send the HTTP GET request
  httpClient.get(url);
  
  // Check for a successful response
  int statusCode = httpClient.responseStatusCode();
  if (statusCode == 200) {
    // Parse the response
    String response = httpClient.responseBody();
    
    // Look for the "feeds" array in the response
    int feedsIndex = response.indexOf("\"feeds\":");
    if (feedsIndex != -1) {
      // Extract the feeds part of the response
      String feedsData = response.substring(feedsIndex + 8); // Move past "feeds": part
      feedsData.trim();  // Remove extra spaces or newline characters

      // Find the first data object in the feeds
      int fieldValueIndex = feedsData.indexOf("\"field" + String(fieldNumber) + "\":");
      if (fieldValueIndex != -1) {
        fieldValueIndex += String("\"field" + String(fieldNumber) + "\":").length(); // Move past the field key

        // Get the field value
        int endIndex = feedsData.indexOf(",", fieldValueIndex);
        if (endIndex == -1) { // If it's the last field in the object
          endIndex = feedsData.indexOf("}", fieldValueIndex);
        }

        String fieldValue = feedsData.substring(fieldValueIndex, endIndex);
        offset  = fieldValue.toFloat();
        
        // Print the value of the field
        Serial.println("Field " + String(fieldNumber) + " value: " + fieldValue);
      } else {
        Serial.println("Field " + String(fieldNumber) + " not found in the response.");
      }
    } else {
      Serial.println("No feeds found in the response.");
    }
  } else {
    Serial.println("HTTP Error: " + String(statusCode));
  }
}



// Wi-Fi Connection Function
void connectToAvailableWiFi() {
  for (size_t i = 0; i < wifiSSIDs.size(); i++) {
    Serial.println("Attempting to connect to WiFi: " + wifiSSIDs[i]);

    WiFi.begin(wifiSSIDs[i].c_str(), wifiPasswords[i].c_str());
    unsigned long startAttemptTime = millis();

    // Wait for connection or timeout after 10 seconds
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 10000) {
      delay(500);
      Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nConnected to WiFi: " + wifiSSIDs[i]);
      ThingSpeak.begin(client);
      return; // Exit function once connected
    } else {
      Serial.println("\nFailed to connect to WiFi: " + wifiSSIDs[i]);
    }
  }

  Serial.println("Unable to connect to any WiFi network. Retrying...");
}
