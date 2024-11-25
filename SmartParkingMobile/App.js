import * as React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import AntDesign from '@expo/vector-icons/AntDesign';
import { screenOptions } from './style';
import SearchScreen from './screens/SearchScreen';
import { useNavigationContainerRef } from '@react-navigation/native';
import ParkingScreen from './screens/ParkingScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function Tabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        ...screenOptions,
        contentStyle: {
          backgroundColor: "white",
        },
      })}
    >
      
      <Tab.Screen
        name="Select Destination"
        component={SearchScreen}
        options={{ tabBarIcon: ({ color, size }) => (<AntDesign name="search1" size={24} color="black" />) }}
      />
    </Tab.Navigator>
  );
}

const AppStack = (
  <>
    <Stack.Screen name="Destination" component={Tabs} options={{ headerShown: false }} />
    <Stack.Screen name="Parking" component={ParkingScreen} options={{ title: 'Parking List' }} />
  </>
);

export default function App() {
  const navigationRef = useNavigationContainerRef();

  return (
    <NavigationContainer ref={navigationRef}>
      <Stack.Navigator>
        {AppStack}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
