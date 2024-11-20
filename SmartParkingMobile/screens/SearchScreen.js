import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, Text, TextInput, View, FlatList, Image, Dimensions, TouchableOpacity, ActivityIndicator, Keyboard } from 'react-native';
import MapView, { Marker } from 'react-native-maps';
import axios from 'axios';
import { googlePlacesApiKey } from '@env';
import PressableButton from '../components/PressableButton';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import haversine from "haversine-distance"; 


const SearchScreen = ({ navigation }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [places, setPlaces] = useState([]);
  const [loading, setLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(true);
  const [selectedPlace, setSelectedPlace] = useState(null);
  const [itemHeights, setItemHeights] = useState({});
  const flatListRef = useRef(null);


  const singaporeLocation = {
    lat: 1.3521,  // Latitude for Singapore
    lng: 103.8198 // Longitude for Singapore
  };
  const [region, setRegion] = useState({
    latitude: singaporeLocation.lat,
    longitude: singaporeLocation.lng,
    latitudeDelta: 0.2,
    longitudeDelta: 0.2,
  });

  useEffect(() => {
    (async () => {
      setLocationLoading(true);

      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        alert('Permission to access current location was denied. Please enable location services in your settings.');
        setLocationLoading(false);
        return;
      }

      setRegion({
        latitude: singaporeLocation.lat,
        longitude: singaporeLocation.lng,
        latitudeDelta: 0.1,
        longitudeDelta: 0.1,
      });

      setLocationLoading(false);
    })();
  }, []);

  const getItemLayout = (data, index) => {
    const height = itemHeights[index] || 0; // Default to 0 if height is not measured yet
    return {
      length: height,
      offset: Object.values(itemHeights).slice(0, index).reduce((sum, h) => sum + h, 0),
      index,
    };
  };

  useEffect(() => {
    if (selectedPlace && places.length > 0 && flatListRef.current) {
      const index = places.findIndex(
        (restaurant) => restaurant.place_id === selectedPlace.place_id
      );
      if (index !== -1) {
        flatListRef.current.scrollToIndex({ index });
      }
    }
  }, [selectedPlace, places]);

  const handleSearchPress = async () => {
    Keyboard.dismiss(); // Hide the keyboard
    setLoading(true);

    const options = {
      method: 'GET',
      url: `https://maps.googleapis.com/maps/api/place/textsearch/json`,
      params: {
        query: searchQuery,
        key: googlePlacesApiKey,
        language: 'en',
        location: `${singaporeLocation.lat},${singaporeLocation.lng}`, // Set Singapore as the location
        radius: 25000, // Radius in meters (25 km to cover entire Singapore)
      },
    };

    try {
      const response = await axios.request(options);
      const singaporeResults=response.data.results.filter((place) =>
        place.formatted_address.includes("Singapore")
    );

      // setPlaces(singaporeResults);
      // 获取用户当前位置
    const userLocation = {
      latitude: singaporeLocation.lat,
      longitude: singaporeLocation.lng,
    };

    // 计算每个地点与用户位置的距离并排序
    const resultsWithDistance = singaporeResults.map((place) => {
      const placeLocation = {
        latitude: place.geometry.location.lat,
        longitude: place.geometry.location.lng,
      };

      const distance = haversine(userLocation, placeLocation); // 距离单位为米
      return { ...place, distance };
    });

    // 按距离排序
    const sortedResults = resultsWithDistance.sort((a, b) => a.distance - b.distance);

    // 设置排序后的结果
    setPlaces(sortedResults);
    
    } catch (error) {
      console.error('Error fetching places:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPhotoUrl = (photoReference) => {
    return `https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${photoReference}&key=${googlePlacesApiKey}`;
  };

  const handlePlacePress = (restaurant) => {
    setSelectedPlace(restaurant);
    navigation.navigate('Parking', { destination: restaurant.geometry.location, currentLocation:region });
  };

  const handleLayout = (index, event) => {
    const { height } = event.nativeEvent.layout;
    setItemHeights((prevHeights) => ({ ...prevHeights, [index]: height }));
  };

  const renderPlace = ({ item, index }) => (
    <TouchableOpacity
      onPress={() => handlePlacePress(item)}
      style={styles.restaurantContainer}
      onLayout={(event) => handleLayout(index, event)}
    >
      {item.photos && item.photos.length > 0 && (
        <Image
          source={{ uri: getPhotoUrl(item.photos[0].photo_reference) }}
          style={styles.restaurantPhoto}
        />
      )}
      <Text style={styles.restaurantName}>{item.name}</Text>
      <Text style={styles.restaurantAddress}>{item.formatted_address}</Text>
      <Text>Rating: {item.rating} stars</Text>
      <Text>Number of Ratings: {item.user_ratings_total}</Text>
    </TouchableOpacity>
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
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search..."
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        <PressableButton onPress={handleSearchPress}>
          <Ionicons name="search" size={24} color="black" />
        </PressableButton>
      </View>
      <MapView style={styles.map} region={region}>
        <Marker
          coordinate={{
            latitude: region.latitude,
            longitude: region.longitude,
          }}
          title="My Location"
          description="This is your current location"
          pinColor="blue"
        />
        {places.map((restaurant) => (
          <Marker
            key={restaurant.place_id}
            coordinate={{
              latitude: restaurant.geometry.location.lat,
              longitude: restaurant.geometry.location.lng,
            }}
            title={restaurant.name}
            description={restaurant.formatted_address}
            onPress={() => setSelectedPlace(restaurant)}
          />
        ))}
      </MapView>
      {loading ? (
        <Text>Loading...</Text>
      ) : (
        <FlatList
          ref={flatListRef}
          data={places}
          keyExtractor={(item) => item.place_id.toString()}
          renderItem={renderPlace}
          ListEmptyComponent={<Text>Enter the Destination and Press One to get the Parking List!</Text>}
          getItemLayout={getItemLayout}
          onScrollToIndexFailed={(info) => {
            console.warn('Failed to scroll to index:', info);
          }}
        />
      )}
    </View>
  );
};

export default SearchScreen;

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
  restaurantContainer: {
    padding: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#ccc',
  },
  restaurantName: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  restaurantAddress: {
    fontSize: 14,
    color: '#666',
  },
  restaurantPhoto: {
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
