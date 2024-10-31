import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, TextInput, View, FlatList, Image, Dimensions, TouchableOpacity, ActivityIndicator, Keyboard } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import axios from 'axios';
import { googlePlacesApiKey } from '@env';
import MapView, { Marker } from 'react-native-maps';


const ParkingScreen = ({ route }) => {
  const navigation = useNavigation();
  const { destination } = route.params;
  const [parkings, setParkings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [locationLoading, setLocationLoading] = useState(true);
  const [region, setRegion] = useState({
    latitude: 49.2827,
    longitude: -123.1207,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  });
  const [selectedParking, setSelectedParking] = useState(null);
  const [itemHeights, setItemHeights] = useState({});
  const flatListRef = useRef(null);

  useEffect(() => {
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

        parkingArray = response.data.results
        const dataAPI = await responseAPI.json();

        const updatedData = parkingArray.map((item1) => {
          // 查找data2中匹配的carpark_number
          const matchingCarpark = dataAPI.items[0].carpark_data.find(
            (item2) => item2.carpark_number === item1.name
          );

          // 如果找到了匹配的carpark_number，则合并carpark_info和update_datetime
          if (matchingCarpark) {
            return {
              ...item1,
              carpark_info_total_lots: matchingCarpark.carpark_info[0].total_lots,
              carpark_info_available_lots: matchingCarpark.carpark_info[0].lots_available,
              update_datetime: matchingCarpark.update_datetime,
            };
          }

          return {
            ...item1,
          };

        });

        const filteredData = updatedData.filter(item => item.update_datetime);
        setParkings(filteredData)
        setLocationLoading(false);
      } catch (error) {
        console.error('Error fetching parking lots:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchParkingLots(); // Fetch parking lots when the component loads
  }, [destination]);

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

      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
        <Text style={styles.parkingName}>{item.name}</Text>
        <Text> - Address: {item.vicinity.replace(/, Singapore/g, "")}</Text>
      </View>
      <Text>Real-time Available Lots: {item.carpark_info_available_lots}/{item.carpark_info_total_lots}</Text>
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
      <MapView style={styles.map} region={destination}>
        <Marker
          coordinate={{
            latitude: destination.lat,
            longitude: destination.lng,
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
            description={parking.formatted_address}
            onPress={() => setSelectedParking(restaurant)}
          />
        ))}
      </MapView>
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
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  searchInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 4,
    padding: 10,
    marginRight: 10,
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
  parkingPhoto: {
    width: '100%',
    height: 150,
    marginTop: 10,
    borderRadius: 4,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
