import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, TextInput, View, FlatList, Image, Dimensions, TouchableOpacity, ActivityIndicator, Keyboard } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import axios from 'axios';
import { googlePlacesApiKey } from '@env';
import {xApiKey} from '@env';
import MapView, { Marker } from 'react-native-maps';
import allParkinglots from './parking_lots_names.js';

const ParkingScreen = ({ route }) => {
  const [currentTime, setCurrentTime] = useState('');
  const [minutesToNextQuarter, setMinutesToNextQuarter] = useState(0);
  const parkingList=allParkinglots;
  // console.log("all parkinglist should be ", parkingList)


  useEffect(() => {
    const now = new Date();
    const timeString = now.toLocaleTimeString(); // 获取当前时间字符串

    const minuteString = now.getMinutes().toString().padStart(2, '0'); // 获取当前分钟数并转换为两位字符串


    const currentMinute = now.getMinutes();
    const nextQuarterMinute = Math.ceil(currentMinute / 15) * 15; // 下一个 15 分钟的倍数
    const minutesRemaining = nextQuarterMinute - currentMinute;

    setMinutesToNextQuarter(minutesRemaining);

    setCurrentTime(currentMinute);
  }, []); // 空依赖数组，确保只在组件加载时执行一次


  const navigation = useNavigation();
  const { destination } = route.params;
  console.log(route.params);
  const [originalParkings, setOriginalParkings] = useState([]); // Store original fetched data
  const [parkings, setParkings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [locationLoading, setLocationLoading] = useState(true);
  const [region, setRegion] = useState({
    latitude: destination.lat,
    longitude: destination.lng,
    latitudeDelta: 0.00175,
    longitudeDelta: 0.00345,
  });
  const [selectedParking, setSelectedParking] = useState(null);
  const [itemHeights, setItemHeights] = useState({});
  const [sortOption, setSortOption] = useState('distance'); // Default sort by distance
  const flatListRef = useRef(null);
  
  // Sorting function based on selected option
  const sortParkings = (data) => {
    const sortedData = [...data]; // Create a shallow copy to avoid modifying the original
    if (sortOption === 'distance') {
      return sortedData; // Already sorted by distance in search results
    } else if (sortOption === 'availableLots') {
      return sortedData.sort((a, b) => b.carpark_info_available_lots - a.carpark_info_available_lots);
    }
    return sortedData;
  };  

  useEffect(() => {

    const fetchPrediction = async (modelName,drivingTime) => {
      try {
        const response = await fetch('https://fb63u8anv3.execute-api.us-west-1.amazonaws.com/prod/predict', {
          method: 'POST',
          headers: {
            'x-api-key': xApiKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            model_name: modelName
          })
        });
  
        const data = await response.json();
        console.log("data is", data)

        function calculateX(A) {
          const quotient = Math.floor(A / 15); // 计算 A / 15 的商
          const remainder = A % 15; // 计算 A / 15 的余数
        
          // 判断余数和 7.5 的大小
          const extra = remainder <= 7.5 ? 0 : 1;
        
          // 计算 X
          const X = quotient + extra;
          if (X > 120) {
            X = 8;
          }
          return X;
        }
        console.log("prediction, driveing time is ",drivingTime)
        const returnDataPoint = calculateX(minutesToNextQuarter+drivingTime/60);
        // code for  test
        // const dataForTest = { predictions: [[0], [15], [30], [45],[60],[75],[90],[105],[120]] };

        // if (dataForTest.predictions && dataForTest.predictions.length > 0) {

        // 更新预测结果
        if (data.predictions && data.predictions.length > 0) {

         
          // console.log("prediction is nihao", data.predictions[0][0])
          // console.log("prediction is nihao", data.predictions[0][0]) // for prediction


          // console.log("[0]is",dataForTest.predictions)
          // console.log("returnDataPoint should be",returnDataPoint)
          // return dataForTest.predictions[returnDataPoint][0]
          // real code
          // return data.predictions[returnDataPoint][0]; 
          console.log("model Name",modelName,'prediction parking lot', data.predictions)
          return data.predictions[0][returnDataPoint]; 

          // setPrediction(data.predictions[0][0]);
        } else {
          return "No predictions found";
          // setPrediction("No predictions found");
        }
      } catch (error) {
        console.error('Error:', error);
        // setPrediction("Error fetching prediction");
      }}

    const getDriveTime = async (location) => {
        if (!route.params.destination) {
          Alert.alert("Wrong location");
          return;
        }
        // {"lat": 1.3816929, "lng": 103.8450516}

        const options = {
          method: 'GET',
          url: 'https://maps.googleapis.com/maps/api/distancematrix/json',
          params: {
            origins: `${route.params.currentLocation.latitude},${route.params.currentLocation.longitude}`,
            // destinations: `1.3816929,103.8450516`,

            // destinations: `${location.lat},${location.lng}`,
            destinations: `${location.lat},${location.lng}`,
            mode: 'driving', // 指定为驾车模式
            key: googlePlacesApiKey,
          },
        };

        try {
          // this is real code
          const response = await axios.request(options);
          const result = response.data.rows[0].elements[0];
          if (result.status === 'OK') {
            console.log("driving time",result.duration.value)
            return result.duration.value // second

          // if (1) {
          //   // console.log("driving time",result.duration.value)
          //   return 1200 // second
          
            // setDriveTime(result.duration.text); // 设置驾车时间
          } else {
            return "cannot get the driving time"
            Alert.alert("cannot get the driving time");
          }
        } catch (error) {
          console.error(error);
          Alert.alert("cannot connect to Google Maps API");
        }
      };

    const fetchParkingLots = async () => {
      setLocationLoading(true);

      const options = {
        method: 'GET',
        url: `https://maps.googleapis.com/maps/api/place/nearbysearch/json`,
        params: {
          location: `${destination.lat},${destination.lng}`, // Use location passed from route.params
          radius: 1000, // 1 km radius
          type: 'parking', // Restrict the search to parking lots
          key: googlePlacesApiKey,
          language: 'en',
        },
      };

      try {
        const response = await axios.request(options);

        const responseAPI = await fetch(
          'https://api.data.gov.sg/v1/transport/carpark-availability'
        );

        parkingArrayBeforeFiltered = response.data.results
        console.log("parkingArray is ",parkingArray)
        const dataAPI = await responseAPI.json();

        const parkingArray = parkingArrayBeforeFiltered.filter(item => parkingList.includes(item.name));


        const updatedData = await Promise.all(parkingArray.map(async (item1) => {
          const matchingCarpark = dataAPI.items[0].carpark_data.find(
            (item2) => item2.carpark_number === item1.name
          );

        // const updatedData = parkingArray.map((item1) => {
        //   // 查找data2中匹配的carpark_number
        //   const matchingCarpark = dataAPI.items[0].carpark_data.find(
        //     (item2) => item2.carpark_number === item1.name
        //   );

          // 如果找到了匹配的carpark_number，则合并carpark_info和update_datetime
          if (matchingCarpark) {
            console.log("item1.name= ",item1.name)
            const drivingTimeFromGoogle = await getDriveTime(item1.geometry.location);
            const predictionFromAPI = await fetchPrediction(item1.name, drivingTimeFromGoogle);

            return {
              ...item1,
              carpark_info_total_lots: matchingCarpark.carpark_info[0].total_lots,
              carpark_info_available_lots: matchingCarpark.carpark_info[0].lots_available,
              prediction: predictionFromAPI,
              update_datetime: matchingCarpark.update_datetime,
              drivingTime:drivingTimeFromGoogle,
            };
          }

          return {
            ...item1,
          };

        }));

        const filteredData = updatedData.filter(item => item.update_datetime);
        setParkings(filteredData);
        setOriginalParkings(sortParkings(filteredData)); // Initially sort and set
        setLocationLoading(false);
      } catch (error) {
        console.error('Error fetching parking lots:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchParkingLots(); // Fetch parking lots when the component loads
  }, [destination]); 

  useEffect(() => {
    if (originalParkings.length > 0) {
      setParkings(sortParkings(originalParkings)); // Sort locally when sort option changes
    }
  }, [sortOption]);

  useEffect(() => {
    if (selectedParking && parkings.length > 0 && flatListRef.current) {
      const index = parkings.findIndex(
        (parking) => parking.place_id === selectedParking.place_id
      );
      if (index !== -1) {
        flatListRef.current.scrollToIndex({ index });
      }
    }
  }, [selectedParking, parkings]);

  function TimeAgo({ datetime }) {
    const calculateTimeDifference = (datetime) => {
      // 将输入的时间转换为 Date 对象
      const updatedTime = new Date(datetime);

      // 获取当前时间，并转换为新加坡时区的时间
      const now = new Date();
      const currentTime = new Date(now);

      // 计算时间差（以毫秒为单位）
      const timeDifference = currentTime - updatedTime;

      // 将时间差转换为分钟
      const minutesAgo = Math.floor(timeDifference / (1000 * 60)) + 900;

      return `${minutesAgo} minutes ago`;
    };

    // 获取当前时间并显示在组件中
    const nowSingapore = new Date().toLocaleString('en-US', { timeZone: 'Asia/Singapore' });

    return (
      <Text>
        Update time: {calculateTimeDifference(datetime)}
      </Text>
    );
  }



  const getItemLayout = (data, index) => {
    const height = itemHeights[index] || 0; // Default to 0 if height is not measured yet
    return {
      length: height,
      offset: Object.values(itemHeights).slice(0, index).reduce((sum, h) => sum + h, 0),
      index,
    };
  };

  const updateMapRegion = (places) => {
    if (places.length === 0) return;

    setRegion({
      latitude: (places[0].geometry.location.lat + region.latitude) / 2,
      longitude: (places[0].geometry.location.lng + region.longitude) / 2,
      latitudeDelta: 0.05,
      longitudeDelta: 0.05,
    });
  };

  const getPhotoUrl = (photoReference) => {
    return `https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${photoReference}&key=${googlePlacesApiKey}`;
  };


  const handleLayout = (index, event) => {
    const { height } = event.nativeEvent.layout;
    setItemHeights((prevHeights) => ({ ...prevHeights, [index]: height }));
  };

  const renderPlace = ({ item, index }) => (
    <View
      style={styles.parkingContainer}
      onLayout={(event) => handleLayout(index, event)}
    >
    {/* <Text >time is: {currentTime}</Text>
    <Text style={styles.timeText}>距离下一个 1/4 小时还有: {minutesToNextQuarter} 分钟</Text> */}


      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <Text style={styles.parkingName}>{item.name}</Text>
        <Text> - Address: {item.vicinity.replace(/, Singapore/g, "")}</Text>
      </View>
      {/* <Text>prediction Lots: {Math.floor(item.prediction)}</Text> */}
      <Text>Driving time: {(item.drivingTime / 60).toFixed(1)} mins</Text>

      {item.drivingTime < 300 ? (
      <Text>Real-time Available Parking Lots: {item.carpark_info_available_lots}/{item.carpark_info_total_lots}</Text>
    ) : (
      <Text>Pridictive Parking Lots: {Math.floor(item.prediction)}/{item.carpark_info_total_lots}</Text>

)}

    </View>
  );

  const getMarkerColor = (availableLots) => {
    if (availableLots > 10) {
      return "green"; 
    } else if (availableLots > 5) {
      return "yellow"; 
    } else {
      return "red";
    }
  };


  const Legend = () => {
    return (
      <View style={styles.legendContainer}>
        <Text style={styles.legendTitle}>Parking Availability</Text>
        <View style={styles.legendRow}>
          <View style={styles.legendItem}>
            <View style={[styles.colorBox, { backgroundColor: 'green' }]} />
            <Text style={styles.legendText}>10+ Lots</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.colorBox, { backgroundColor: 'yellow' }]} />
            <Text style={styles.legendText}>5-10 Lots</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.colorBox, { backgroundColor: 'red' }]} />
            <Text style={styles.legendText}>{"<"} 5 Lots</Text>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.colorBox, { backgroundColor: 'blue' }]} />
            <Text style={styles.legendText}>Destination</Text>
          </View>
        </View>
      </View>
    );
  };

   // Render sort buttons
   const renderSortButtons = () => (
    <View style={styles.buttonContainer}>
      <TouchableOpacity
        style={[styles.sortButton, sortOption === 'availableLots' && styles.activeButton]}
        onPress={() => setSortOption('availableLots')}
      >
        <Text style={[styles.buttonText, sortOption === 'availableLots' && styles.activeButtonText]}>Sort by Available Lots</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.sortButton, sortOption === 'distance' && styles.activeButton]}
        onPress={() => setSortOption('distance')}
      >
        <Text style={[styles.buttonText, sortOption === 'distance' && styles.activeButtonText]}>Sort by Distance</Text>
      </TouchableOpacity>
    </View>
  );

  

  if (locationLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0000ff" />
        <Text>Fetching location...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <MapView style={styles.map} region={region}>
        <Marker
          coordinate={{
            latitude: region.latitude,
            longitude: region.longitude,
          }}
          title="Destination"
          description="This is your destination"
          pinColor="blue"
        />
        {parkings.map((parking) => (
          <Marker
            key={parking.place_id}
            coordinate={{
              latitude: parking.geometry.location.lat,
              longitude: parking.geometry.location.lng,
            }}
            title={parking.name}
            description={parking.drivingTime < 300 ?
              `Available: ${parking.carpark_info_available_lots}/${parking.carpark_info_total_lots}`:
            `Available: ${parking.prediction}/${parking.carpark_info_total_lots}`}
            
            pinColor={
              parking.drivingTime < 300
        ? getMarkerColor(parking.carpark_info_available_lots)
        : getMarkerColor(Math.floor(parking.prediction))
              
              }
            
            onPress={() => setSelectedParking(parking)}
            tracksViewChanges={true}
          />
        ))}
      </MapView>
      <Legend />
      {renderSortButtons()}
      {loading ? (
        <Text>Loading...</Text>
      ) : (
        <FlatList
          ref={flatListRef}
          data={parkings}
          keyExtractor={(item) => item.place_id.toString()}
          renderItem={renderPlace}
          ListEmptyComponent={<Text>Sorry! There is no public parking lot nearby!</Text>}
          getItemLayout={getItemLayout}
          onScrollToIndexFailed={(info) => {
            console.warn('Failed to scroll to index:', info);
          }}
        />
      )}

    </View>
  );
};

export default ParkingScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 10,
    paddingLeft: 0,
  },
  map: {
    width: Dimensions.get('window').width,
    height: Dimensions.get('window').height * 0.2,
  },
  parkingContainer: {
    padding: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#ccc',
  },
  parkingName: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  parkingAddress: {
    fontSize: 14,
    color: '#666',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  legendContainer: {
    padding: 10,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderColor: '#ccc',
  },
  legendTitle: {
    fontWeight: 'bold',
    marginBottom: 5,
    textAlign: 'center',
  },
  legendRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 5,
  },
  colorBox: {
    width: 15,
    height: 15,
    marginRight: 5,
    borderRadius: 3,
  },
  legendText: {
    fontSize: 14,
    color: '#333',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 6,
  },
  sortButton: {
    flex: 1, // Make both buttons take equal space
    paddingVertical: 5,
    borderRadius: 5,
    backgroundColor: 'lightgrey', // Light gray background for inactive button
    marginHorizontal: 5,
    alignItems: 'center', // Center text within the button
  },
  activeButton: {
    backgroundColor: '#007AFF', // Blue background for active button
  },
  buttonText: {
    color: '#8E8E93', // Light gray text for inactive button
    fontSize: 15,
    fontWeight: 'bold',
  },
  activeButtonText: {
    color: 'white', // White text for active button
  },
});
