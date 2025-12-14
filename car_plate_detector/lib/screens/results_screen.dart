import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'dart:io';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

class ResultsScreen extends StatefulWidget {
  final Map<String, dynamic> detectionResult;
  final String imagePath;
  final ApiService apiService;
  final bool isManualInput;

  const ResultsScreen({
    Key? key,
    required this.detectionResult,
    required this.imagePath,
    required this.apiService,
    this.isManualInput = false,
  }) : super(key: key);

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  late PlateDetectionResult _result;

  @override
  void initState() {
    super.initState();
    _parseResults();
    _saveScanLog();
  }

  void _parseResults() {
    final platesDetected = widget.detectionResult['plates_detected'] as List?;
    if (platesDetected != null && platesDetected.isNotEmpty) {
      _result = PlateDetectionResult.fromJson(
        platesDetected[0] as Map<String, dynamic>,
      );
    }
  }

  Future<void> _saveScanLog() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final logsJson = prefs.getStringList('scan_logs') ?? [];

      final log = {
        'plateNumber': _result.plateNumber,
        'scanTime': DateTime.now().toIso8601String(),
        'violationCount': _result.violations.violationCount,
        'hasViolations': _result.violations.hasViolations,
        'source': widget.isManualInput ? 'manual' : 'camera',
      };

      logsJson.add(jsonEncode(log));
      await prefs.setStringList('scan_logs', logsJson);
    } catch (e) {
      debugPrint('Error saving scan log: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Detection Results'), elevation: 2),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Original Image
            Container(
              margin: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey[300]!),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(
                  File(widget.imagePath),
                  height: 250,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              ),
            ),
            // Plate Information Card
            _buildPlateCard(),
            // Violations Card
            if (_result.violations.hasViolations)
              _buildViolationsCard()
            else
              _buildNoViolationsCard(),
            // Owner Information Card
            if (_result.ownerInfo.found) _buildOwnerCard(),
            // Cropped Plate Image
            if (_result.croppedPlateImage.isNotEmpty) _buildCroppedPlateCard(),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildPlateCard() {
    final alertColor = _result.alertStatus.isFlagged
        ? Colors.red[700]
        : Colors.green[700];

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'License Plate',
                  style: TextStyle(fontSize: 14, color: Colors.grey),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: alertColor?.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _result.alertStatus.alertLevel.toUpperCase(),
                    style: TextStyle(
                      color: alertColor,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              _result.plateNumber,
              style: const TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                fontFamily: 'monospace',
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildConfidenceItem(
                    'Detection',
                    _result.detectionConfidence,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildConfidenceItem('OCR', _result.ocrConfidence),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildConfidenceItem(String label, double confidence) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        const SizedBox(height: 4),
        Row(
          children: [
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: confidence,
                  minHeight: 6,
                  backgroundColor: Colors.grey[300],
                  valueColor: AlwaysStoppedAnimation<Color>(
                    confidence > 0.8 ? Colors.green : Colors.orange,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '${(confidence * 100).toStringAsFixed(1)}%',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildViolationsCard() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: Colors.red[50],
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.warning, color: Colors.red[700]),
                const SizedBox(width: 8),
                Text(
                  'Violations Found',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.red[700],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildViolationStat(
                    'Count',
                    '${_result.violations.violationCount}',
                    Colors.red,
                  ),
                  _buildViolationStat(
                    'Total Fine',
                    '₱${_result.violations.totalFine.toStringAsFixed(0)}',
                    Colors.orange,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            ..._result.violations.violationDetails
                .map((violation) => _buildViolationItem(violation))
                .toList(),
          ],
        ),
      ),
    );
  }

  Widget _buildNoViolationsCard() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: Colors.green[50],
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.check_circle, color: Colors.green[700]),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'No Violations Found',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.green[700],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildViolationStat(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        const SizedBox(height: 4),
        Text(
          value,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
      ],
    );
  }

  Widget _buildViolationItem(ViolationDetail violation) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                violation.type,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: violation.isPaid ? Colors.green[100] : Colors.red[100],
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  violation.isPaid ? 'PAID' : 'UNPAID',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: violation.isPaid
                        ? Colors.green[700]
                        : Colors.red[700],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Fine: ₱${violation.fineAmount.toStringAsFixed(0)}',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
          ),
          if (violation.location != null) ...[
            const SizedBox(height: 4),
            Text(
              'Location: ${violation.location}',
              style: TextStyle(fontSize: 12, color: Colors.grey[600]),
            ),
          ],
          const SizedBox(height: 4),
          Text(
            'Date: ${violation.date}',
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  Widget _buildOwnerCard() {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.person, color: Colors.blue[700]),
                const SizedBox(width: 8),
                const Text(
                  'Owner Information',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_result.ownerInfo.ownerName != null) ...[
              _buildOwnerField('Name', _result.ownerInfo.ownerName!),
            ],
            if (_result.ownerInfo.ownerPhone != null) ...[
              _buildOwnerField('Phone', _result.ownerInfo.ownerPhone!),
            ],
            if (_result.ownerInfo.ownerEmail != null) ...[
              _buildOwnerField('Email', _result.ownerInfo.ownerEmail!),
            ],
            if (_result.ownerInfo.vehicleType != null) ...[
              _buildOwnerField('Vehicle Type', _result.ownerInfo.vehicleType!),
            ],
            if (_result.ownerInfo.vehicleColor != null) ...[
              _buildOwnerField(
                'Vehicle Color',
                _result.ownerInfo.vehicleColor!,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildOwnerField(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$label: ',
            style: const TextStyle(fontSize: 13, color: Colors.grey),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCroppedPlateCard() {
    // Extra safety check for empty image path
    if (_result.croppedPlateImage.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Cropped License Plate',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey[300]!),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  widget.apiService.getCroppedPlateImageUrl(
                    _result.croppedPlateImage,
                  ),
                  height: 150,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      height: 150,
                      color: Colors.grey[200],
                      child: const Center(child: Text('Image not available')),
                    );
                  },
                  loadingBuilder: (context, child, loadingProgress) {
                    if (loadingProgress == null) return child;
                    return Container(
                      height: 150,
                      color: Colors.grey[200],
                      child: const Center(child: CircularProgressIndicator()),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
