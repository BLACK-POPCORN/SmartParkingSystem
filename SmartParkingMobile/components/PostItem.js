import React, { useState, useEffect } from 'react';
import { View, Text, Image, StyleSheet, Pressable } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import PressableButton from './PressableButton';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { ref, getDownloadURL } from 'firebase/storage';
import { auth, storage } from '../Firebase/firebaseSetup'; // Import Firebase storage setup
import { colors, commonStyles } from '../style';
import { FIREBASE_COLLECTIONS } from '../FirebaseCollection';
import { fetchArrayDataByField, updateLikeStatus, writeWithIdToDB, deleteWithIdFromDB } from '../Firebase/firestoreHelper';
import { getUserName } from '../Firebase/firestoreHelper';

// Define collection name
const COLLECTION_NAME = FIREBASE_COLLECTIONS.POSTS;

const PostItem = ({ item, onPress }) => {
  // State to store the number of likes (size of likedBy array)
  const [likesCount, setLikesCount] = useState(0);
  const [imageUrl, setImageUrl] = useState(null);
  // State to track if the post is liked by the current user
  const [isFavorite, setIsFavorite] = useState(false);
  const [authorName, setAuthorName] = useState('Anonymous');
  const currentUserId = auth.currentUser.uid;

  // useEffect to fetch the image URL from Firebase Storage
  useEffect(() => {
    async function fetchImageUrl() {
      try {
        const imageRef = ref(storage, item.imageUrls[0]);
        const url = await getDownloadURL(imageRef);
        setImageUrl(url);
      } catch (error) {
        console.error('Error fetching image URL:', error);
        // Optionally set a fallback image or handle error
      }
    }

    const fetchAuthorName = async () => {
      try {
        const name = await getUserName(item.author);
        setAuthorName(name || 'Anonymous');
      } catch (error) {
        console.error('Error fetching author name:', error);
      }
    };

    // Check if there is an image URL to fetch
    if (item.imageUrls && item.imageUrls[0]) {
      fetchImageUrl();
    }
    fetchAuthorName();
  }, [item]);


  async function fetchLikeData() {
    try {
      const likedBy = await fetchArrayDataByField(COLLECTION_NAME, item.id, 'likedBy');
      setIsFavorite(likedBy.includes(currentUserId));
      setLikesCount(likedBy.length);
    } catch (error) {
      console.error('Error checking if post is liked:', error);
    }
  }

  useFocusEffect(
    React.useCallback(() => {
      fetchLikeData();
    }, [item.id])
  );

  // Function to handle the like button press
  const handleLikePress = async () => {
    const newFavoriteState = !isFavorite; // Toggle the favorite state

    setIsFavorite(newFavoriteState); // Update the local favorite state

    try {
      await updateLikeStatus(COLLECTION_NAME, item.id, 'likedBy', currentUserId, newFavoriteState);
      setLikesCount(newFavoriteState ? likesCount + 1 : likesCount - 1); // Update the local likes count
    } catch (error) {
      console.error('Error updating likes in Firestore:', error);
      // Optionally handle error, e.g., rollback the like count in UI
    }

    try {
      if (newFavoriteState) {
        await writeWithIdToDB({timestamp:new Date(), post_id: item.id}, `User/${currentUserId}/FavoritePost`, item.id);
      }
      else {
        await deleteWithIdFromDB(`User/${currentUserId}/FavoritePost`, item.id);
      }
    } catch (error) {
      console.error('Error inserting likes to FavoritePosts in Firestore:', error);
    }
  };


  return (
    <View style={styles.card}>
      <Pressable onPress={() => onPress(item)}>
        <Image source={{ uri: imageUrl || 'fallback_image_url' }} style={styles.cardImage} />
        <Text style={styles.cardTitle}>{item.title}</Text>
      </Pressable>
      <View style={styles.cardFooter}>
        <Text style={styles.cardAuthor}>{authorName}</Text>

        <View style={commonStyles.likeSection}>
          <PressableButton onPress={handleLikePress}>
            <Icon
              name={isFavorite ? 'heart' : 'heart-outline'} // Toggle between filled and outline
              size={18}
              color={isFavorite ? colors.favorite : colors.notFavorite} // Toggle color
            />
          </PressableButton>
          <Text style={commonStyles.cardLikes}>{likesCount}</Text>
        </View>
      </View>

    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    width: '48%',
    backgroundColor: colors.background,
    marginBottom: 10,
    borderRadius: 10,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.itemBorder,
    flexDirection: 'column', // Arrange children vertically
    justifyContent: 'space-between', // Distribute space to move footer to bottom
  },
  cardImage: {
    width: '100%',
    height: 120,
  },
  cardTitle: {
    padding: 10,
    fontSize: 14,
    color: colors.textDark,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingBottom: 10,
    marginTop: 'auto', // Pushes footer to the bottom
  },
  cardAuthor: {
    fontSize: 12,
    color: colors.textLight,
  },
});

export default PostItem;
