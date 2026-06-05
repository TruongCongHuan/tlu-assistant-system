// lib/services/stt_service.dart
import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_recognition_error.dart';

enum SttState { idle, listening, processing, unavailable }

class SttService extends ChangeNotifier {
  final stt.SpeechToText _speech = stt.SpeechToText();

  SttState _state         = SttState.idle;
  String   _currentWords  = '';
  double   _soundLevel    = 0.0;     // 0.0 - 1.0 cho waveform animation
  bool     _initialized   = false;

  SttState get state        => _state;
  String   get currentWords => _currentWords;
  double   get soundLevel   => _soundLevel;
  bool     get isListening  => _state == SttState.listening;
  bool     get isIdle       => _state == SttState.idle;

  // ── Khởi tạo (gọi 1 lần) ─────────────────────────────
  Future<bool> initialize() async {
    if (_initialized) return true;

    // Xin permission microphone
    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      _state = SttState.unavailable;
      notifyListeners();
      return false;
    }

    _initialized = await _speech.initialize(
      onError: _onError,
      onStatus: _onStatus,
      debugLogging: false,
    );

    if (!_initialized) {
      _state = SttState.unavailable;
    }
    notifyListeners();
    return _initialized;
  }

  // ── Bắt đầu lắng nghe ────────────────────────────────
  Future<void> startListening({
    required void Function(String text) onResult,
    void Function(String finalText)? onFinal,
  }) async {
    if (!_initialized) {
      final ok = await initialize();
      if (!ok) return;
    }

    _currentWords = '';
    _state        = SttState.listening;
    notifyListeners();

    await _speech.listen(
      onResult: (SpeechRecognitionResult result) {
        _currentWords = result.recognizedWords;
        notifyListeners();
        onResult(_currentWords);

        if (result.finalResult) {
          _state = SttState.processing;
          notifyListeners();
          onFinal?.call(_currentWords);
          // Auto-stop sau final result
          Future.delayed(const Duration(milliseconds: 200), stop);
        }
      },
      onSoundLevelChange: (level) {
        // level: -2 to 10 dBFS → normalize to 0.0 - 1.0
        _soundLevel = ((level + 2) / 12).clamp(0.0, 1.0);
        notifyListeners();
      },
      // ── Cấu hình cho tiếng Việt ──────────────────────
      localeId: 'vi_VN',
      listenMode: stt.ListenMode.dictation,
      pauseFor: const Duration(seconds: 3),     // Dừng tự động sau 3s im lặng
      listenFor: const Duration(seconds: 60),   // Max 60s
      cancelOnError: true,
      partialResults: true,                      // Hiển thị text real-time
    );
  }

  // ── Dừng lắng nghe ───────────────────────────────────
  Future<void> stop() async {
    if (isListening) {
      await _speech.stop();
    }
    _state     = SttState.idle;
    _soundLevel = 0.0;
    notifyListeners();
  }

  // ── Cancel (không lấy kết quả) ───────────────────────
  Future<void> cancel() async {
    await _speech.cancel();
    _currentWords = '';
    _state        = SttState.idle;
    _soundLevel   = 0.0;
    notifyListeners();
  }

  void _onError(SpeechRecognitionError error) {
    debugPrint('[STT] Error: ${error.errorMsg} (permanent: ${error.permanent})');
    _state        = SttState.idle;
    _soundLevel   = 0.0;
    notifyListeners();
  }

  void _onStatus(String status) {
    debugPrint('[STT] Status: $status');
    if (status == 'done' || status == 'notListening') {
      if (_state == SttState.listening) {
        _state    = SttState.idle;
        _soundLevel = 0.0;
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _speech.cancel();
    super.dispose();
  }
}
