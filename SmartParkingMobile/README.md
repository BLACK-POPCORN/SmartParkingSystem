# Mobile development for Smart Parking System

This mobile application based on REACT-NATIVE framework consists of two screens. The SearchScreen from `SearchScreen.js` is the screen showed the destination results searched by users. The ParkingScreen from `ParkingScreen.js` is the screen showed the parking lots nearby the destination.

## How to use this application

```bash
cd SmartParkingMobile
npm install 
npm start
```
You need to install EXPO on your mobile device and connect to the same network.

In order to run this application, you need to create a `.env` file in this folder(`/SmartSmartParkingMobile`). It contains two parts: 

```bash
googlePlacesApiKey = "AIzaSyA5RsGAZpN_-d9QsbQVcfObJ9wweZ9V-J8" 
xApiKey = "DkWrgFBeBi4GrgNn0b4gU1lXd2SdbloXaQhPT9LZ"
```
`googlePlacesApiKey` is the key required to run the Google Map service.

`xApiKey` is the key to connect to AWS for interaction.

## The process of application

When the app is launched, the SearchScreen will be displayed. The SearchScreen contains a search box, a search button, a map, and a place to display results.


![Start Screen](../assets/startScreen.png)

Suppose the user searches for `stadium`. After pressing the search button, the application will call the Google Map API to find matching results. The results will be marked on the map in the form of a Marker and in the result list below. The Marker on the map will show the name of the place, and the list below will jump to the corresponding place.

Suppose the user selects `Toa Payoh ActiveSG Stadium`, the program will jump to the next screen `ParkingScreen.js` to display the parking lot.

![Search For Stadium](../assets/searchForStadium.png)

In this screen, the parking lot information near the destination will be displayed. Due to the different number of parking lots, user need to wait for a while.

![Loading](../assets/loading.png)

When the program jumps to this interface, Google Map will return a list of all nearby parking lots (whether public or private), and then the program will filter with the list of all public parking lots managed by the Singapore government provided in `parking_lots_names.js`, and then call the Singapore public parking API to obtain real-time data, as well as the API of our prediction system running on AWS. In addition, the Google Map API will also be called to obtain the driving time. Finally, the corresponding predicted data will be displayed based on the driving time. If the driving time is less than 5 minutes, the real-time parking space data will be displayed, and if it is more than 5 minutes, the predicted data will be displayed.

![Parking Log](../assets/parkingLot.png)

When the loading is complete, the specific information of the parking lot will be displayed below, and the location of the parking lot will also be marked on the map in the form of a Marker. Different colors represent the number of parking spaces. Similarly, clicking the parking lot marker on the map will jump to the corresponding parking lot specific information below.

The parking lot list below will display detailed information, including the parking lot's name, address, driving time from your current location to the parking lot, the distance from the parking lot to your destination, and available parking spaces.

![details of Parking Lot](../assets/detailOfParkingLot.png)


Clicking the corresponding parking lot `TPMR` will direct to Google Map for navigation.

![navigation](../assets/navigation.png)


