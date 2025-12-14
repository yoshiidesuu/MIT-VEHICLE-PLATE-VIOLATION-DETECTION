// yolo_client.dart
// Dart/Flutter client for YOLO Instance Segmentation API

import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io';

class Detection {
  final int id;
  final String className;
  final double confidence;
  final BBox bbox;

  Detection({
    required this.id,
    required this.className,
    required this.confidence,
    required this.bbox,
  });

  factory Detection.fromJson(Map<String, dynamic> json) {
    return Detection(
      id: json['id'] ?? 0,
      className: json['class'] ?? 'unknown',
      confidence: (json['confidence'] ?? 0).toDouble(),
      bbox: BBox.fromJson(json['bbox'] ?? {}),
    );
  }
}

class BBox {
  final double x1;
  final double y1;
  final double x2;
  final double y2;

  BBox({
    required this.x1,
    required this.y1,
    required this.x2,
    required this.y2,
  });

  double get width => x2 - x1;
  double get height => y2 - y1;
  double get centerX => (x1 + x2) / 2;
  double get centerY => (y1 + y2) / 2;

  factory BBox.fromJson(Map<String, dynamic> json) {
    return BBox(
      x1: (json['x1'] ?? 0).toDouble(),
      y1: (json['y1'] ?? 0).toDouble(),
      x2: (json['x2'] ?? 0).toDouble(),
      y2: (json['y2'] ?? 0).toDouble(),
    );
  }
}

class PredictionResult {
  final bool success;
  final String timestamp;
  final List<int> imageShape;
  final List<Detection> detections;
  final String? resultImage;

  PredictionResult({
    required this.success,
    required this.timestamp,
    required this.imageShape,
    required this.detections,
    this.resultImage,
  });

  factory PredictionResult.fromJson(Map<String, dynamic> json) {
    var detectionsJson = json['detections'] as List? ?? [];
    return PredictionResult(
      success: json['success'] ?? false,
      timestamp: json['timestamp'] ?? '',
      imageShape: List<int>.from(json['image_shape'] ?? []),
      detections: detectionsJson
          .map((d) => Detection.fromJson(d as Map<String, dynamic>))
          .toList(),
      resultImage: json['result_image'],
    );
  }
}

class GPUInfo {
  final bool gpuAvailable;
  final int deviceCount;
  final int currentDevice;
  final String deviceName;
  final String? cudaVersion;
  final String pytorchVersion;
  final String memoryAllocated;
  final String memoryReserved;

  GPUInfo({
    required this.gpuAvailable,
    required this.deviceCount,
    required this.currentDevice,
    required this.deviceName,
    this.cudaVersion,
    required this.pytorchVersion,
    required this.memoryAllocated,
    required this.memoryReserved,
  });

  factory GPUInfo.fromJson(Map<String, dynamic> json) {
    return GPUInfo(
      gpuAvailable: json['gpu_available'] ?? false,
      deviceCount: json['device_count'] ?? 0,
      currentDevice: json['current_device'] ?? -1,
      deviceName: json['device_name'] ?? 'Unknown',
      cudaVersion: json['cuda_version'],
      pytorchVersion: json['pytorch_version'] ?? 'Unknown',
      memoryAllocated: json['memory_allocated'] ?? 'N/A',
      memoryReserved: json['memory_reserved'] ?? 'N/A',
    );
  }
}

class HealthStatus {
  final String status;
  final String timestamp;
  final String device;
  final String? gpuMemory;

  HealthStatus({
    required this.status,
    required this.timestamp,
    required this.device,
    this.gpuMemory,
  });

  factory HealthStatus.fromJson(Map<String, dynamic> json) {
    return HealthStatus(
      status: json['status'] ?? 'unknown',
      timestamp: json['timestamp'] ?? '',
      device: json['device'] ?? 'cpu',
      gpuMemory: json['gpu_memory'],
    );
  }
}

class YOLOClient {
  final String baseUrl;
  final http.Client httpClient;

  YOLOClient({required this.baseUrl, http.Client? httpClient})
    : httpClient = httpClient ?? http.Client();

  /// Check server health status
  Future<HealthStatus> getHealth() async {
    try {
      final response = await httpClient
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return HealthStatus.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Health check failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Health check error: $e');
    }
  }

  /// Get GPU information
  Future<GPUInfo> getGPUInfo() async {
    try {
      final response = await httpClient
          .get(Uri.parse('$baseUrl/gpu-info'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return GPUInfo.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('GPU info request failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('GPU info error: $e');
    }
  }

  /// Get model information
  Future<Map<String, dynamic>> getModelInfo() async {
    try {
      final response = await httpClient
          .get(Uri.parse('$baseUrl/model-info'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Model info request failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Model info error: $e');
    }
  }

  /// Perform instance segmentation on a single image
  Future<PredictionResult> predict(File imageFile) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/predict'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('file', imageFile.path),
      );

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 60),
      );

      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return PredictionResult.fromJson(jsonDecode(response.body));
      } else {
        final errorBody = jsonDecode(response.body);
        throw Exception(errorBody['detail'] ?? 'Prediction failed');
      }
    } catch (e) {
      throw Exception('Prediction error: $e');
    }
  }

  /// Process multiple images at once
  Future<List<Map<String, dynamic>>> predictBatch(List<File> imageFiles) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/predict-batch'),
      );

      for (var file in imageFiles) {
        request.files.add(
          await http.MultipartFile.fromPath('files', file.path),
        );
      }

      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 120),
      );

      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        return List<Map<String, dynamic>>.from(body['results'] ?? []);
      } else {
        throw Exception('Batch prediction failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Batch prediction error: $e');
    }
  }

  /// Get saved result image
  Future<Uint8List> getResultImage(String filename) async {
    try {
      final response = await httpClient
          .get(Uri.parse('$baseUrl/results/$filename'))
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return response.bodyBytes;
      } else {
        throw Exception('Failed to get result image');
      }
    } catch (e) {
      throw Exception('Get result image error: $e');
    }
  }

  /// List all saved results
  Future<List<String>> listResults() async {
    try {
      final response = await httpClient
          .get(Uri.parse('$baseUrl/results'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        return List<String>.from(body['files'] ?? []);
      } else {
        throw Exception('Failed to list results');
      }
    } catch (e) {
      throw Exception('List results error: $e');
    }
  }

  /// Clear all saved results
  Future<void> clearResults() async {
    try {
      final response = await httpClient
          .post(Uri.parse('$baseUrl/clear-results'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception('Failed to clear results');
      }
    } catch (e) {
      throw Exception('Clear results error: $e');
    }
  }
}

// Example usage in Flutter:
//
// final yolo = YOLOClient(baseUrl: 'http://192.168.1.100:8000');
//
// // Check server
// final health = await yolo.getHealth();
// print('Server: ${health.status}');
// print('GPU: ${health.device}');
//
// // Get GPU info
// final gpuInfo = await yolo.getGPUInfo();
// print('GPU Available: ${gpuInfo.gpuAvailable}');
// print('CUDA: ${gpuInfo.cudaVersion}');
//
// // Predict on image
// final imageFile = File('/path/to/image.jpg');
// final result = await yolo.predict(imageFile);
// print('Detections: ${result.detections.length}');
// for (var det in result.detections) {
//   print('${det.className}: ${(det.confidence * 100).toStringAsFixed(1)}%');
// }
