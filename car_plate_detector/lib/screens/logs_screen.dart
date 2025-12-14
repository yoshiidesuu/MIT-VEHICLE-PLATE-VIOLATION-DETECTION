import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class ScanLog {
  final String plateNumber;
  final DateTime scanTime;
  final int violationCount;
  final bool hasViolations;
  final String source; // 'camera' or 'manual'

  ScanLog({
    required this.plateNumber,
    required this.scanTime,
    required this.violationCount,
    required this.hasViolations,
    required this.source,
  });

  Map<String, dynamic> toJson() => {
    'plateNumber': plateNumber,
    'scanTime': scanTime.toIso8601String(),
    'violationCount': violationCount,
    'hasViolations': hasViolations,
    'source': source,
  };

  factory ScanLog.fromJson(Map<String, dynamic> json) => ScanLog(
    plateNumber: json['plateNumber'] as String,
    scanTime: DateTime.parse(json['scanTime'] as String),
    violationCount: json['violationCount'] as int,
    hasViolations: json['hasViolations'] as bool,
    source: json['source'] as String,
  );
}

class LogsScreen extends StatefulWidget {
  const LogsScreen({Key? key}) : super(key: key);

  @override
  State<LogsScreen> createState() => _LogsScreenState();
}

class _LogsScreenState extends State<LogsScreen> {
  late SharedPreferences _prefs;
  List<ScanLog> _logs = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadLogs();
  }

  Future<void> _loadLogs() async {
    try {
      _prefs = await SharedPreferences.getInstance();
      final logsJson = _prefs.getStringList('scan_logs') ?? [];

      setState(() {
        _logs = logsJson
            .map((log) => ScanLog.fromJson(jsonDecode(log)))
            .toList();
        _logs.sort((a, b) => b.scanTime.compareTo(a.scanTime));
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error loading logs: $e')));
      }
    }
  }

  Future<void> _clearLogs() async {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear All Logs'),
        content: const Text(
          'Are you sure you want to delete all scan logs? This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              _prefs.remove('scan_logs');
              setState(() => _logs.clear());
              Navigator.pop(context);
              ScaffoldMessenger.of(
                context,
              ).showSnackBar(const SnackBar(content: Text('Logs cleared')));
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  Future<void> _deleteLog(int index) async {
    _logs.removeAt(index);
    final logsJson = _logs.map((log) => jsonEncode(log.toJson())).toList();
    await _prefs.setStringList('scan_logs', logsJson);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Logs'),
        elevation: 2,
        actions: [
          if (_logs.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: _clearLogs,
              tooltip: 'Clear all logs',
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _logs.isEmpty
          ? _buildEmptyState()
          : Column(
              children: [
                // Statistics
                if (_logs.isNotEmpty) _buildStatistics(),
                // Logs List
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _logs.length,
                    itemBuilder: (context, index) {
                      final log = _logs[index];
                      return _buildLogItem(context, log, index);
                    },
                  ),
                ),
              ],
            ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              color: Colors.grey[200],
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.history, size: 50, color: Colors.grey[400]),
          ),
          const SizedBox(height: 24),
          Text(
            'No Scan Logs Yet',
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            'Scan plates to see the history here',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  Widget _buildStatistics() {
    final totalScans = _logs.length;
    final withViolations = _logs.where((l) => l.hasViolations).length;
    final totalViolations = _logs.fold(
      0,
      (sum, log) => sum + log.violationCount,
    );

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.blue[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue[200]!),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStat('Total Scans', '$totalScans', Colors.blue),
          _buildStat('With Violations', '$withViolations', Colors.red),
          _buildStat('Total Violations', '$totalViolations', Colors.orange),
        ],
      ),
    );
  }

  Widget _buildStat(String label, String value, Color color) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
      ],
    );
  }

  Widget _buildLogItem(BuildContext context, ScanLog log, int index) {
    final dateTime =
        '${log.scanTime.day}/${log.scanTime.month}/${log.scanTime.year} ${log.scanTime.hour}:${log.scanTime.minute.toString().padLeft(2, '0')}';
    final sourceIcon = log.source == 'camera' ? Icons.camera_alt : Icons.edit;
    final sourceLabel = log.source == 'camera' ? 'Camera' : 'Manual';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[200]!),
        color: Colors.white,
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.all(16),
        leading: Container(
          width: 50,
          height: 50,
          decoration: BoxDecoration(
            color: log.hasViolations ? Colors.red[100] : Colors.green[100],
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            log.hasViolations ? Icons.warning : Icons.check_circle,
            color: log.hasViolations ? Colors.red[700] : Colors.green[700],
          ),
        ),
        title: Text(
          log.plateNumber,
          style: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            fontFamily: 'monospace',
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(sourceIcon, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(sourceLabel, style: TextStyle(color: Colors.grey[600])),
                const SizedBox(width: 12),
                Icon(Icons.access_time, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(dateTime, style: TextStyle(color: Colors.grey[600])),
              ],
            ),
            const SizedBox(height: 6),
            if (log.hasViolations)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.red[100],
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '${log.violationCount} violation${log.violationCount > 1 ? 's' : ''}',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.red[700],
                    fontWeight: FontWeight.w600,
                  ),
                ),
              )
            else
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.green[100],
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'No violations',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.green[700],
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
          ],
        ),
        trailing: IconButton(
          icon: Icon(Icons.delete, color: Colors.red[400]),
          onPressed: () => _deleteLog(index),
        ),
      ),
    );
  }
}
