import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, TextInput, View, FlatList, Image, Dimensions, TouchableOpacity, ActivityIndicator, Keyboard } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import axios from 'axios';
import { googlePlacesApiKey } from '@env';


const ParkingScreen = ({ route }) => {
  const navigation = useNavigation();
  const {destination} = route.params;
  const [parkings, setParkings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(true);
  const [region, setRegion] = useState({
    latitude: 49.2827,
    longitude: -123.1207,
    latitudeDelta: 0.05,
    longitudeDelta: 0.05,
  });
  const [selectParking, setSelectParking] = useState(null);
  const [itemHeights, setItemHeights] = useState({});
  const flatListRef = useRef(null);


  const [parkingData, setParkingData] = useState([]);

  const [carparkNumber, setCarparkNumber] = useState([]);



  useEffect(() => {
    const fetchParkingLots = async () => {
      setLocationLoading(true);

      const options = {
        method: 'GET',
        url: `https://maps.googleapis.com/maps/api/place/nearbysearch/json`,
        params: {
          location: `${destination.lat},${destination.lng}`, // Use location passed from route.params
          radius: 1000, // 2 km radius
          type: 'parking', // Restrict the search to parking lots
          key: googlePlacesApiKey,
          language: 'en',
        },
      };

      try {
        const response = await axios.request(options);
        // console.log(response.data.results)


        const responseAPI = await fetch(
          'https://api.data.gov.sg/v1/transport/carpark-availability'
        );
        
        parkingArray=response.data.results
        const dataAPI = await responseAPI.json(); 


        const extractNames = (parkingArray) => {
          return parkingArray.map(item => item.name);
        };
      
        // Create dataname array
        const dataFromgoogle = extractNames(parkingArray);
        
        console.log("datafromgoogle",dataFromgoogle)
  

        const filteredData = dataAPI.items[0].carpark_data.filter((item) =>
          dataFromgoogle.includes(item.carpark_number)
        ); // 过滤匹配的停车场
        setParkingData(filteredData); // 设置过滤后的数据

        // console.log("dataAPIItems",dataAPIItems)

 


        setParkings(response.data.results); // Use the search results for parking lots
        updateMapRegion(response.data.results);
        // fetchParkingData();
        // console.log(parkings)

      } catch (error) {
        console.error('Error fetching parking lots:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchParkingLots(); // Fetch parking lots when the component loads
  }, [destination]);


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

  // const renderPlace = ({ item, index }) => (
  //   <View
  //     style={styles.parkingContainer}
  //     onLayout={(event) => handleLayout(index, event)}
  //   >
  //     {/* {item.photos && item.photos.length > 0 && (
  //       <Image
  //         source={{ uri: getPhotoUrl(item.photos[0].photo_reference) }}
  //         style={styles.parkingPhoto}
  //       />
  //     )} */}
  //     <Text style={styles.parkingName}>{item.name}</Text>
  //     <Text style={styles.parkingAddress}>{item.formatted_address}</Text>
  //     {/* Get parking name through  'item.name' */}
  //     <Text>Available parking spot(according to api): TODO!!!</Text>
  //     </View>
  // );

  const renderParkingItem = ({ item }) => (
    <View
    style={styles.parkingContainer}
  >
      <Text style={styles.parkingName}>Carpark: {item.carpark_number}</Text>
      <Text style={styles.parkingText}>Total lots: {item.carpark_info[0].total_lots}</Text>
      <Text style={styles.parkingText}>Available lots: {item.carpark_info[0].lots_available}</Text>
      <Text style={styles.parkingText}>Last updated: {item.update_datetime}</Text>
    </View>
  );



  return (
    <View style={styles.container}>
      {loading ? (
        <Text>Loading...</Text>
      ) : (
        // <FlatList
        //   ref={flatListRef}
        //   data={parkings}
        //   keyExtractor={(item) => item.place_id.toString()}
        //   renderItem={renderPlace}
        //   ListEmptyComponent={<Text>Sorry! There is no parking lot nearby!</Text>}
        //   getItemLayout={getItemLayout}
        //   onScrollToIndexFailed={(info) => {
        //     console.warn('Failed to scroll to index:', info);
        //   }}
        // />

        <FlatList
          data={parkingData}
          renderItem={renderParkingItem}
          keyExtractor={(item) => item.carpark_number.toString()}
          ListEmptyComponent={<Text>Sorry! There is no public parking lot nearby!</Text>}
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
