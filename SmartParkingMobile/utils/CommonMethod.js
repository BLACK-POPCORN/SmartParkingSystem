import axios from 'axios';
import { googlePlacesApiKey } from '@env'; // Ensure that your API key is set up correctly
import { ref, getDownloadURL } from 'firebase/storage';
import { storage } from '../Firebase/firebaseSetup';

// Function to fetch place details from Google Places API
export const fetchPlaceDetails = async (place_id) => {
  try {
    const response = await axios.get('https://maps.googleapis.com/maps/api/place/details/json', {
      params: {
        place_id: place_id,
        key: googlePlacesApiKey,
        fields: 'name,rating,formatted_address,photos,types,geometry',
      },
    });
    return response.data.result;
  } catch (error) {
    console.error('Error fetching place details:', error);
    return null;
  }
};

// Function to fetch image URLs from Firebase Storage
export const fetchImageUrls = async (imageUris) => {
  try {
      const urls = await Promise.all(
          imageUris.map(async (imageUri) => {
              const imageRef = ref(storage, imageUri);
              const url = await getDownloadURL(imageRef);
              return url;
          })
      );
      return urls;
  } catch (error) {
      console.error('Error fetching image URLs: ', error);
      throw error; // Rethrow the error so the caller can handle it
  }
};
