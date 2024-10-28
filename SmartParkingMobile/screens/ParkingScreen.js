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

        const responseAPI = await fetch(
          'https://api.data.gov.sg/v1/transport/carpark-availability'
        );
        
        parkingArray=response.data.results
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
          
          // 如果没有匹配，返回原来的data1对象
          // return {
          //   ...item1,
          //   carpark_info_total_lots: 'N/A',
          //   carpark_info_available_lots: 'N/A',
          //   update_datetime: 'N/A',
          // };

          return {
            ...item1,
          };
          
        });
        const filteredData = updatedData.filter(item => item.update_datetime);
        setParkings(filteredData)
        console.log(parkings);
        // setMergedData(updatedData);


        // const extractNames = (parkingArray) => {
        //   return parkingArray.map(item => item.name);
        // };
      
        // // Create dataname array
        // const dataFromgoogle = extractNames(parkingArray);
        
        // console.log("datafromgoogle",dataFromgoogle)
  

        // const filteredData = dataAPI.items[0].carpark_data.filter((item) =>
        //   dataFromgoogle.includes(item.carpark_number)
        // ); // 过滤匹配的停车场
        // setParkingData(filteredData); // 设置过滤后的数据

        // console.log("dataAPIItems",dataAPIItems)


        // setParkings(response.data.results); // Use the search results for parking lots
        // updateMapRegion(response.data.results);

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
      const timeDifference = currentTime - updatedTime ;
  
      // 将时间差转换为分钟
      const minutesAgo = Math.floor(timeDifference / (1000 * 60))+900;
  
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
      


      {item.photos && item.photos.length > 0 && (
        <Image
          source={{ uri: getPhotoUrl(item.photos[0].photo_reference) }}
          style={styles.parkingPhoto}
        />
      )}
      <Text style={styles.parkingName}>{item.name}</Text>      
      {/* <Text style={styles.parkingName}>{item.carpark_data}</Text>

      <Text style={styles.parkingAddress}>{item.formatted_address}</Text> */}

      <Text>percentage of available lots: {((item.carpark_info_available_lots / item.carpark_info_total_lots) * 100).toFixed()}%
      ({item.carpark_info_available_lots}/{item.carpark_info_total_lots})
      </Text>
      {/* <Text style={styles.parkingName}>carpark_info_available_lots: </Text> */}
      <TimeAgo datetime={item.update_datetime} />

      <Text >address: {item.vicinity}</Text>

      {/* Get parking name through  'item.name' */}
      {/* <Text>Available parking spot(according to api): TODO!!!</Text> */}
      </View>



  );


  return (
    <View style={styles.container}>
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
