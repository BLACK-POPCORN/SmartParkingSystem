import { StyleSheet } from 'react-native';

// Define colors for the app
export const colors = {
    background: '#fff',
    currentLocation: 'blue',
    textDark: '#333',
    textLight: '#777',
    orchidBG: 'mediumorchid',
    headerText: '#FFFFFF',
    rippleEffect: 'darkseagreen',
    alertIcon: '#FFD700',
    border: '#ccc',
    borderBottom: '#eee',
    postButtonBg: '#ff3b30',
    pressedButton: '#aaa',
    white: '#ffffff',
    favorite: 'hotpink',
    notFavorite: '#AAA',
    restaurantSecBg: 'lemonchiffon',
    commentText:'#888',
    likeBg: 'paleturquoise',
    addCommentButton: '#4CAF50',
    loadingBg:'rgba(255, 255, 255, 0.7)',
    dividerBg: 'rgba(204, 204, 204, 0.3)',
    deleteButtonBg: 'rgba(0, 0, 0, 0.5)',
    itemBorder:'#eee',
};
// Define common styles used across the app
export const commonStyles = StyleSheet.create({
    likeSection: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    cardLikes: {
        fontSize: 14,
        color: '#777',
    },
})

// Define screen options for navigators
export const screenOptions = {
    headerStyle: {
        backgroundColor: colors.orchidBG,
    },
    headerTintColor: colors.headerText,
    tabBarStyle: { backgroundColor: colors.orchidBG },
    tabBarActiveTintColor: colors.alertIcon,
    tabBarInactiveTintColor: colors.headerText,
};