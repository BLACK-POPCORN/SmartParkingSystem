import React, { useState, useEffect } from 'react';
import { View, Image, StyleSheet, Text, TouchableOpacity, FlatList, Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker'; // Import image picker from Expo
import { MaterialIcons } from '@expo/vector-icons'; // Import icons for UI
import { ref, deleteObject } from 'firebase/storage';
import { storage } from '../Firebase/firebaseSetup'; // Adjust the path as needed
import { colors } from '../style';

const ImagePickerComponent = ({ initialImages = [], onImageSelect, onRemoveImage, isEditMode = false }) => {
  const [selectedImages, setSelectedImages] = useState([]); // State to store the selected image URIs

  useEffect(() => {
    setSelectedImages(initialImages);
  }, [initialImages]);

  // Function to request camera permissions
  const requestCameraPermissions = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Camera Permission Required', 'Please grant camera permission to use this feature.');
      return false;
    }
    return true;
  };

  // Function to request media library permissions
  const requestMediaLibraryPermissions = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Media Library Permission Required', 'Please grant media library permission to use this feature.');
      return false;
    }
    return true;
  };

  // Function to pick multiple images from the gallery
  const pickImages = async () => {
    const hasPermission = await requestMediaLibraryPermissions(); // Check for permissions
    if (!hasPermission) return;

    if (selectedImages.length >= 9) {
      Alert.alert('Limit Reached', 'You can only select up to 9 images.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images, // Only allow image selection
      allowsMultipleSelection: true, // Allow multiple selection
      selectionLimit: 9 - selectedImages.length, // Limit based on already selected images
      quality: 1, // Image quality setting
    });

    // Check if the images were not canceled and set them
    if (!result.canceled) {
      const newUris = result.assets.map((asset) => asset.uri);
      const uniqueUris = newUris.filter((uri) => !selectedImages.includes(uri)); // Filter out already selected images
      const updatedImages = [...selectedImages, ...uniqueUris].slice(0, 9); // Ensure no more than 9 images

      setSelectedImages(updatedImages);
      if (typeof onImageSelect === 'function') {
        onImageSelect(updatedImages); // Pass the updated image URIs to the parent component
      }
    }
  };

  // Function to take a photo using the camera
  const takePhoto = async () => {
    const hasPermission = await requestCameraPermissions(); // Check for permissions
    if (!hasPermission) return;

    if (selectedImages.length >= 9) {
      Alert.alert('Limit Reached', 'You can only select up to 9 images.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true, // Allow editing of the captured image
      aspect: [4, 3], // Aspect ratio for the image
      quality: 1, // Image quality setting
    });

    // Check if the image was not canceled and set it
    if (!result.canceled) {
      const uri = result.assets[0].uri;
      if (!selectedImages.includes(uri)) {
        // Check if the photo is not already selected
        const updatedImages = [...selectedImages, uri].slice(0, 9); // Append new photo, ensure max 9

        setSelectedImages(updatedImages);
        if (typeof onImageSelect === 'function') {
          onImageSelect(updatedImages); // Pass the updated image URIs to the parent component
        }
      }
    }
  };

  // Function to remove an image from the selection
  const removeImage = (uri) => {
    const updatedImages = selectedImages.filter((imageUri) => imageUri !== uri);
    setSelectedImages(updatedImages);
    if (typeof onImageSelect === 'function') {
      onImageSelect(updatedImages);
    }

    // Notify the parent component if the image should be removed from storage
    if (isEditMode && typeof onRemoveImage === 'function') {
      const isStoredInStorage = uri.startsWith("https://firebasestorage.googleapis.com");
      onRemoveImage(uri, isStoredInStorage);
    }
  };

  // Render each image in a grid with delete functionality
  const renderImage = ({ item }) => (
    <View style={styles.imageContainer}>
      <Image source={{ uri: item }} style={styles.image} />
      <TouchableOpacity
        style={styles.deleteButton}
        onPress={() => removeImage(item)}
      >
        <MaterialIcons name="close" size={20} color="white" />
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>

      {/* Image Gallery */}
      <FlatList
        data={selectedImages}
        renderItem={renderImage}
        keyExtractor={(item, index) => index.toString()}
        numColumns={3} // Display images in 3 columns
        ListEmptyComponent={
          <View style={styles.placeholder}>
            <Text>No Images</Text>
          </View>
        }
      />
      {/* Button Container */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.button} onPress={pickImages}>
          <MaterialIcons name="add-photo-alternate" size={24} color="black" />
          <Text>Add Photos</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.button} onPress={takePhoto}>
          <MaterialIcons name="photo-camera" size={24} color="black" />
          <Text>Take Photo</Text>
        </TouchableOpacity>
      </View>

      
    </View>
  );
};

// Styles for the component
const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    padding: 20,
  },
  imageContainer: {
    position: 'relative',
    marginBottom:5
  },
  image: {
    width: 85,
    height: 85,
    borderRadius: 10,
  },
  deleteButton: {
    position: 'absolute',
    top: 5,
    right: 5,
    backgroundColor: colors.deleteButtonBg, // Semi-transparent background for visibility
    borderRadius: 15,
    width: 30,
    height: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholder: {
    width: 80,
    height: 80,
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 10,
    marginBottom: 10,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '80%',
    marginTop: 10,
  },
  button: {
    alignItems: 'center',
    padding: 6,
  },
});

export default ImagePickerComponent;
