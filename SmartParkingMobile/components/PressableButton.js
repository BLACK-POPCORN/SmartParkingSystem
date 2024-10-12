import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors } from '../style';

const PressableButton = ({ children, onPress, style }) => {
    return (
        <Pressable
            android_ripple={{ color: colors.rippleEffect }}
            style={({ pressed }) => [
                {
                    opacity: pressed ? 0.5 : 1,
                },
                styles.button,
                style,
            ]}
            onPress={onPress}
        >
            <View>
                {children}
            </View>
        </Pressable>
    );
};

const styles = StyleSheet.create({
    button: {
        // marginRight: 5,
        borderRadius: 8,
        paddingVertical: 10,
        paddingHorizontal: 15,
        alignItems: 'center',
    },
});

export default PressableButton;
