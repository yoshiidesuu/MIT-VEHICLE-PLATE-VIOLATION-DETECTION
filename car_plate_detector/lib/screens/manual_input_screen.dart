import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'results_screen.dart';

class ManualInputScreen extends StatefulWidget {
  const ManualInputScreen({Key? key}) : super(key: key);

  @override
  State<ManualInputScreen> createState() => _ManualInputScreenState();
}

class _ManualInputScreenState extends State<ManualInputScreen> {
  late TextEditingController _plateController;
  final ApiService _apiService = ApiService();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _plateController = TextEditingController();
  }

  @override
  void dispose() {
    _plateController.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> _parseViolationDetails(dynamic violations) {
    if (violations == null) return [];
    if (violations is! List) return [];

    return violations
        .map((v) {
          if (v is Map) {
            return Map<String, dynamic>.from(v as Map);
          }
          return <String, dynamic>{};
        })
        .toList()
        .cast<Map<String, dynamic>>();
  }

  Future<void> _checkPlate() async {
    final plate = _plateController.text.trim();
    if (plate.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a license plate number')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final violationResult = await _apiService.getViolations(plate);
      final vehicleResult = await _apiService.getVehicleInfo(plate);

      if (violationResult != null && mounted) {
        // Build detection result from manual input
        final detectionResult = {
          'plates_detected': [
            {
              'plate_number': plate,
              'detection_confidence': 1.0,
              'ocr_confidence': 1.0,
              'cropped_plate_image': '',
              'violations': {
                'has_violations': violationResult['has_violations'] ?? false,
                'violation_count': violationResult['violation_count'] ?? 0,
                'total_fine': violationResult['total_fine'] ?? 0,
                'is_flagged': violationResult['has_violations'] ?? false,
                'violation_details': _parseViolationDetails(
                  violationResult['violations'] ?? [],
                ),
              },
              'owner_info': vehicleResult ?? {'found': false},
              'alert_status': {
                'is_flagged': violationResult['has_violations'] ?? false,
                'alert_level': (violationResult['has_violations'] ?? false)
                    ? 'high'
                    : 'normal',
                'message': (violationResult['has_violations'] ?? false)
                    ? '⚠️ ${violationResult['violation_count'] ?? 0} violations found'
                    : '✓ No violations',
              },
            },
          ],
        };

        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ResultsScreen(
              detectionResult: detectionResult,
              imagePath: '',
              apiService: _apiService,
              isManualInput: true,
            ),
          ),
        );
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Plate not found in database')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Manual Plate Check'), elevation: 2),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 20),
              // Icon
              Center(
                child: Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.edit, size: 50, color: Colors.orange[700]),
                ),
              ),
              const SizedBox(height: 32),
              // Title
              Text(
                'Check License Plate',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Enter a license plate number to check for violations and owner information',
                style: Theme.of(
                  context,
                ).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
              ),
              const SizedBox(height: 40),
              // Input Field
              TextField(
                controller: _plateController,
                textCapitalization: TextCapitalization.characters,
                decoration: InputDecoration(
                  hintText: 'e.g., MH 02 AB 1234',
                  hintStyle: TextStyle(color: Colors.grey[400]),
                  prefixIcon: const Icon(Icons.directions_car),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: Colors.grey[300]!),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: Colors.blue[700]!),
                  ),
                  filled: true,
                  fillColor: Colors.grey[50],
                ),
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.5,
                ),
                onSubmitted: (_) => _checkPlate(),
              ),
              const SizedBox(height: 24),
              // Format Info
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue[200]!),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info, color: Colors.blue[700], size: 20),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Format: State Code + Registration + Letters + Numbers\nExample: MH 02 AB 1234',
                        style: TextStyle(fontSize: 12, color: Colors.blue[700]),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 40),
              // Check Button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _checkPlate,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.orange[700],
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: Colors.grey[300],
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.white,
                            ),
                          ),
                        )
                      : const Text(
                          'Check Plate',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                ),
              ),
              const SizedBox(height: 40),
              // Recent Searches
              if (_plateController.text.isNotEmpty) ...[
                Text(
                  'Tip',
                  style: Theme.of(
                    context,
                  ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(
                  'Make sure to enter the plate number exactly as shown on the vehicle',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
