// lib/services/tts_service.dart
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

enum TtsState { playing, stopped, paused }

class TtsService extends ChangeNotifier {
  late FlutterTts _tts;
  TtsState _state  = TtsState.stopped;
  String?  _playingId; // ID của message đang đọc

  TtsState get state     => _state;
  String?  get playingId => _playingId;
  bool get isPlaying     => _state == TtsState.playing;

  TtsService() {
    _tts = FlutterTts();
    _init();
  }

  Future<void> _init() async {
    // ── Language ─────────────────────────────────────
    await _tts.setLanguage('vi-VN');

    // ── Voice settings ────────────────────────────────
    await _tts.setSpeechRate(0.5);   // 0.0 - 1.0 (Gemini default ~0.5)
    await _tts.setVolume(1.0);
    await _tts.setPitch(1.0);

    // ── iOS specific ──────────────────────────────────
    if (Platform.isIOS) {
      await _tts.setSharedInstance(true);
      await _tts.setIosAudioCategory(
        IosTextToSpeechAudioCategory.playback,
        [
          IosTextToSpeechAudioCategoryOptions.allowBluetooth,
          IosTextToSpeechAudioCategoryOptions.allowBluetoothA2DP,
          IosTextToSpeechAudioCategoryOptions.mixWithOthers,
        ],
        IosTextToSpeechAudioMode.defaultMode,
      );
    }

    // ── Android specific ──────────────────────────────
    if (Platform.isAndroid) {
      await _tts.setQueueMode(1); // Add to queue
    }

    // ── Callbacks ─────────────────────────────────────
    _tts.setStartHandler(() {
      _state = TtsState.playing;
      notifyListeners();
    });

    _tts.setCompletionHandler(() {
      _state     = TtsState.stopped;
      _playingId = null;
      notifyListeners();
    });

    _tts.setCancelHandler(() {
      _state     = TtsState.stopped;
      _playingId = null;
      notifyListeners();
    });

    _tts.setErrorHandler((msg) {
      debugPrint('[TTS] Error: $msg');
      _state     = TtsState.stopped;
      _playingId = null;
      notifyListeners();
    });
  }

  // ── Speak một đoạn text ───────────────────────────────
  Future<void> speak(String text, {String? messageId}) async {
    // Nếu đang đọc cùng message → dừng (toggle)
    if (_playingId == messageId && isPlaying) {
      await stop();
      return;
    }

    await stop(); // Dừng bất kỳ thứ gì đang đọc
    _playingId = messageId;

    // Làm sạch text trước khi đọc (bỏ markdown)
    final cleanText = _stripMarkdown(text);
    await _tts.speak(cleanText);
  }

  Future<void> stop() async {
    if (_state != TtsState.stopped) {
      await _tts.stop();
      _state     = TtsState.stopped;
      _playingId = null;
      notifyListeners();
    }
  }

  Future<void> pause() async {
    if (Platform.isAndroid && isPlaying) {
      await _tts.pause();
      _state = TtsState.paused;
      notifyListeners();
    }
  }

  // ── Kiểm tra ngôn ngữ có sẵn không ───────────────────
  Future<bool> isVietnameseAvailable() async {
    final langs = await _tts.getLanguages;
    return (langs as List).any(
      (l) => l.toString().toLowerCase().contains('vi'),
    );
  }

  // ── Strip markdown để TTS đọc tự nhiên hơn ───────────
  String _stripMarkdown(String text) {
    return text
        .replaceAll(RegExp(r'\*\*(.*?)\*\*'), r'$1') // **bold**
        .replaceAll(RegExp(r'\*(.*?)\*'), r'$1')     // *italic*
        .replaceAll(RegExp(r'`(.*?)`'), r'$1')       // `code`
        .replaceAll(RegExp(r'#{1,6}\s'), '')          // # headers
        .replaceAll(RegExp(r'\[(.*?)\]\(.*?\)'), r'$1') // [link](url)
        .replaceAll(RegExp(r'[-*+]\s'), '')           // list items
        .replaceAll(RegExp(r'\n{2,}'), '. ')          // double newlines
        .replaceAll('\n', ' ')
        .trim();
  }

  @override
  void dispose() {
    _tts.stop();
    super.dispose();
  }
}
