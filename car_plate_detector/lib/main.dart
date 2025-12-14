import 'package:flutter/material.dart';
import 'screens/landing_screen.dart';

void main() {
  runApp(const CarPlateDetectorApp());
}

class CarPlateDetectorApp extends StatelessWidget {
  const CarPlateDetectorApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Car Plate Detector',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      home: const LandingScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}
