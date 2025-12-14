import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class PlateDetectionResult {
  final String plateNumber;
  final double detectionConfidence;
  final double ocrConfidence;
  final String croppedPlateImage;
  final ViolationInfo violations;
  final OwnerInfo ownerInfo;
  final AlertStatus alertStatus;

  PlateDetectionResult({
    required this.plateNumber,
    required this.detectionConfidence,
    required this.ocrConfidence,
    required this.croppedPlateImage,
    required this.violations,
    required this.ownerInfo,
    required this.alertStatus,
  });

  factory PlateDetectionResult.fromJson(Map<String, dynamic> json) {
    return PlateDetectionResult(
      plateNumber: json['plate_number'] ?? 'Unknown',
      detectionConfidence: (json['detection_confidence'] ?? 0.0).toDouble(),
      ocrConfidence: (json['ocr_confidence'] ?? 0.0).toDouble(),
      croppedPlateImage: json['cropped_plate_image'] ?? '',
      violations: ViolationInfo.fromJson(json['violations'] ?? {}),
      ownerInfo: OwnerInfo.fromJson(json['owner_info'] ?? {}),
      alertStatus: AlertStatus.fromJson(json['alert_status'] ?? {}),
    );
  }
}

class ViolationInfo {
  final bool hasViolations;
  final int violationCount;
  final double totalFine;
  final bool isFlagged;
  final String? lastViolationDate;
  final List<ViolationDetail> violationDetails;

  ViolationInfo({
    required this.hasViolations,
    required this.violationCount,
    required this.totalFine,
    required this.isFlagged,
    this.lastViolationDate,
    required this.violationDetails,
  });

  factory ViolationInfo.fromJson(Map<String, dynamic> json) {
    var details = <ViolationDetail>[];
    if (json['violation_details'] != null) {
      details = List<ViolationDetail>.from(
        (json['violation_details'] as List).map(
          (v) => ViolationDetail.fromJson(v as Map<String, dynamic>),
        ),
      );
    }
    return ViolationInfo(
      hasViolations: json['has_violations'] ?? false,
      violationCount: json['violation_count'] ?? 0,
      totalFine: (json['total_fine'] ?? 0.0).toDouble(),
      isFlagged: json['is_flagged'] ?? false,
      lastViolationDate: json['last_violation_date'],
      violationDetails: details,
    );
  }
}

class ViolationDetail {
  final int id;
  final String type;
  final String date;
  final String? location;
  final double fineAmount;
  final bool isPaid;
  final String? description;

  ViolationDetail({
    required this.id,
    required this.type,
    required this.date,
    this.location,
    required this.fineAmount,
    required this.isPaid,
    this.description,
  });

  factory ViolationDetail.fromJson(Map<String, dynamic> json) {
    return ViolationDetail(
      id: json['id'] ?? 0,
      type: json['type'] ?? 'Unknown',
      date: json['date'] ?? '',
      location: json['location'],
      fineAmount: (json['fine_amount'] ?? 0.0).toDouble(),
      isPaid: json['is_paid'] ?? false,
      description: json['description'],
    );
  }
}

class OwnerInfo {
  final bool found;
  final String? ownerName;
  final String? ownerPhone;
  final String? ownerEmail;
  final String? vehicleType;
  final String? vehicleColor;
  final bool isActive;

  OwnerInfo({
    required this.found,
    this.ownerName,
    this.ownerPhone,
    this.ownerEmail,
    this.vehicleType,
    this.vehicleColor,
    required this.isActive,
  });

  factory OwnerInfo.fromJson(Map<String, dynamic> json) {
    return OwnerInfo(
      found: json['found'] ?? false,
      ownerName: json['owner_name'],
      ownerPhone: json['owner_phone'],
      ownerEmail: json['owner_email'],
      vehicleType: json['vehicle_type'],
      vehicleColor: json['vehicle_color'],
      isActive: json['is_active'] ?? true,
    );
  }
}

class AlertStatus {
  final bool isFlagged;
  final String alertLevel;
  final String message;

  AlertStatus({
    required this.isFlagged,
    required this.alertLevel,
    required this.message,
  });

  factory AlertStatus.fromJson(Map<String, dynamic> json) {
    return AlertStatus(
      isFlagged: json['is_flagged'] ?? false,
      alertLevel: json['alert_level'] ?? 'normal',
      message: json['message'] ?? 'No violations',
    );
  }
}

class ApiService {
  // For Android emulator: use 10.0.2.2 to reach host machine
  // For physical device: use your machine's IP address
  // For web/desktop: use localhost
  static const String baseUrl = 'http://10.0.2.2:8000';
  static const String apiV1 = '$baseUrl/api';

  final Dio _dio;

  ApiService({Dio? dio}) : _dio = dio ?? Dio();

  Future<Map<String, dynamic>?> detectPlate(String imagePath) async {
    try {
      FormData formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(imagePath),
      });

      final response = await _dio.post(
        '$baseUrl/detect-plates',
        data: formData,
        options: Options(
          contentType: 'multipart/form-data',
          followRedirects: true,
          validateStatus: (status) => true,
        ),
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        debugPrint('Error: ${response.statusCode} - ${response.statusMessage}');
        return null;
      }
    } catch (e) {
      debugPrint('Exception: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> getViolations(String plateNumber) async {
    try {
      final response = await _dio.get('$baseUrl/violations/check/$plateNumber');

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('Exception: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> getVehicleInfo(String plateNumber) async {
    try {
      final response = await _dio.get('$baseUrl/vehicles/info/$plateNumber');

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('Exception: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> getDatabaseStatus() async {
    try {
      final response = await _dio.get('$baseUrl/database/status');

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('Exception: $e');
      return null;
    }
  }

  String getCroppedPlateImageUrl(String filename) {
    return '$baseUrl/cropped-plate/$filename';
  }
}
