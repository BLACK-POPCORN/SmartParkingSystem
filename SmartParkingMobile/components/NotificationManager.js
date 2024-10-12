import { StyleSheet, Text, View, Button } from 'react-native'
import React from 'react'
import * as Notifications from "expo-notifications";


export const verifyPermission = async () =>{
    try {
        const permission = await Notifications.getPermissionsAsync();
        if (permission.granted === false) {
            const newPermission = await Notifications.requestPermissionsAsync();
            return permission.granted;
        }
   
        return permission.granted;
    } catch (err) {
        console.log(err);
    }
}
const NotificationManager = () => {
    const scheduleNotificationHandler = async () => {
        try {
            const hasPermission = await verifyPermission();
            if (!hasPermission) {
                return;
            }
            const data = await Notifications.scheduleNotificationAsync({
                content: {
                    title: "Add a goal",
                    body: "Don't forget to add a goal today!",
                    data:{url:"https://www.google.com"}
                },
                trigger: {
                    seconds: 5,
                },
            });
            console.log("Scheduled a notification: ", data);
        } catch (err) {
            console.log(err);
        }
        
    }
  return (
    <View>
      <Button title="Remind me to add a goal" onPress={scheduleNotificationHandler}/>
    </View>
  )
}

export default NotificationManager

const styles = StyleSheet.create({})