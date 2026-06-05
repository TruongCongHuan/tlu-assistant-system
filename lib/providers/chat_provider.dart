// lib/providers/chat_provider.dart
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../config/api_config.dart';
import '../config/app_runtime_config.dart';
import '../config/demo_report_config.dart';
import '../models/conversation.dart';
import '../services/local_rag_service.dart';
import '../services/remote_rag_service.dart';

const _kUseRemoteRag = 'use_remote_rag';

String _formatErrorForUser(Object e) {
  if (e is StateError) {
    final m = e.message;
    if (m.isNotEmpty) return m;
  }
  final s = e.toString();
  // Tránh cắt nhầm "Bad state: ..." thành chỉ "Bad state"
  return s;
}

class ChatProvider extends ChangeNotifier {
  static const _uuid = Uuid();

  final LocalRagService _localRag = LocalRagService();
  final RemoteRagService _remoteRag = RemoteRagService();

  final List<ChatMessage> _messages = [];
  List<ChatMessage> get messages => List.unmodifiable(_messages);

  bool _isThinking = false;
  bool get isThinking => _isThinking;

  late bool _useRemoteRag;
  bool get useRemoteRag => _useRemoteRag;

  String? _activeDocId;
  String? get activeDocId => _activeDocId;

  /// [initialUseRemoteRag] đọc từ `main()` (SharedPreferences) để tránh race:
  /// `_loadRemotePref` async trong constructor từng ghi đè lại `false` sau khi user bật công tắc.
  ChatProvider({bool initialUseRemoteRag = false}) : _useRemoteRag = initialUseRemoteRag {
    if (DemoReportConfig.enabled && AppRuntimeConfig.useStaticDemo) {
      _seedDemoAiChat();
    }
  }

  void _seedDemoAiChat() {
    final now = DateTime.now();
    _messages.addAll([
      ChatMessage(
        id: 'demo_ai_1',
        text: 'Giải thích khái niệm đệ quy cho sinh viên mới học lập trình',
        role: MessageRole.user,
        createdAt: now.subtract(const Duration(minutes: 8)),
      ),
      ChatMessage(
        id: 'demo_ai_2',
        text:
            '**Đệ quy** là cách một hàm tự gọi lại chính nó với bài toán **nhỏ hơn**, '
            'cho đến khi gặp **điều kiện dừng**.\n\n'
            'Ví dụ tính giai thừa n!: n! = n × (n-1)!, với 0! = 1.\n\n'
            'Với em học KHMT năm nhất, nên vẽ **cây gọi hàm** khi làm bài tập — '
            'dễ tránh lặp vô hạn.',
        role: MessageRole.assistant,
        createdAt: now.subtract(const Duration(minutes: 7)),
      ),
    ]);
  }

  Future<void> setUseRemoteRag(bool value) async {
    _useRemoteRag = value;
    final p = await SharedPreferences.getInstance();
    await p.setBool(_kUseRemoteRag, value);
    // doc_id trên server (Chroma) khác UUID local SQLite — bật remote thì bỏ lọc tài liệu local.
    if (value) {
      _activeDocId = null;
    }
    notifyListeners();
  }

  void setActiveDoc(String? docId) {
    _activeDocId = docId;
    notifyListeners();
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;

    if (DemoReportConfig.enabled && AppRuntimeConfig.useStaticDemo) {
      _messages.add(ChatMessage(
        id: _uuid.v4(),
        text: text.trim(),
        role: MessageRole.user,
        createdAt: DateTime.now(),
      ));
      _isThinking = true;
      notifyListeners();
      await Future<void>.delayed(const Duration(milliseconds: 600));
      _messages.add(ChatMessage(
        id: _uuid.v4(),
        text:
            'TLU AI đã nhận câu hỏi của em **${DemoReportConfig.studentShortName}** '
            '(${DemoReportConfig.studentProgram}, ${DemoReportConfig.studentYear}).\n\n'
            'Em có thể hỏi thêm về lộ trình học, đăng ký tín chỉ hoặc liên hệ '
            '**Cố vấn học tập** / các phòng ban qua menu Chat.',
        role: MessageRole.assistant,
        createdAt: DateTime.now(),
      ));
      _isThinking = false;
      notifyListeners();
      return;
    }

    if (_useRemoteRag && !ApiConfig.isRemoteConfigured) {
      _messages.add(ChatMessage(
        id: _uuid.v4(),
        text:
            'Đã bật RAG qua server nhưng thiếu cấu hình. Thêm:\n'
            '--dart-define=API_BASE_URL=https://... \n'
            '--dart-define=STUDENT_API_KEY=...',
        role: MessageRole.assistant,
        status: MessageStatus.error,
        createdAt: DateTime.now(),
      ));
      notifyListeners();
      return;
    }

    _messages.add(ChatMessage(
      id: _uuid.v4(),
      text: text.trim(),
      role: MessageRole.user,
      createdAt: DateTime.now(),
    ));
    _isThinking = true;
    notifyListeners();

    final aiMsgId = _uuid.v4();
    _messages.add(ChatMessage(
      id: aiMsgId,
      text: '',
      role: MessageRole.assistant,
      status: MessageStatus.sending,
      createdAt: DateTime.now(),
    ));
    notifyListeners();

    try {
      final buffer = StringBuffer();
      final useRemote = _useRemoteRag && ApiConfig.isRemoteConfigured;
      if (kDebugMode) {
        debugPrint(
          '[ChatProvider] useRemoteRag=$_useRemoteRag '
          'apiConfigured=${ApiConfig.isRemoteConfigured} → stream=${useRemote ? "remote" : "local"}',
        );
      }
      final stream = useRemote
          ? _remoteRag.queryStream(text, docId: _activeDocId)
          : _localRag.queryStream(text, docId: _activeDocId);

      await for (final chunk in stream) {
        buffer.write(chunk);
        _updateAiMessage(aiMsgId, buffer.toString(), MessageStatus.sending);
      }

      _updateAiMessage(aiMsgId, buffer.toString(), MessageStatus.done);
    } catch (e) {
      _updateAiMessage(
        aiMsgId,
        'Xin lỗi, đã xảy ra lỗi: ${_formatErrorForUser(e)}',
        MessageStatus.error,
      );
    }

    _isThinking = false;
    notifyListeners();
  }

  void _updateAiMessage(String id, String text, MessageStatus status) {
    final idx = _messages.indexWhere((m) => m.id == id);
    if (idx < 0) return;
    _messages[idx] = _messages[idx].copyWith(text: text, status: status);
    notifyListeners();
  }

  void clearMessages() {
    _messages.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    _remoteRag.close();
    super.dispose();
  }
}
