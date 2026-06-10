// lib/providers/chat_provider.dart
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../config/api_config.dart';
import '../config/app_runtime_config.dart';
import '../config/demo_report_config.dart';
import '../models/conversation.dart';
import '../models/rag_stream.dart';
import '../services/local_rag_service.dart';
import '../services/rag_feedback_service.dart';
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

  /// [initialUseRemoteRag] đọc từ `main()` (SharedPreferences) để tránh race.
  ChatProvider({bool initialUseRemoteRag = true}) : _useRemoteRag = initialUseRemoteRag {
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

    final userText = text.trim();
    _messages.add(ChatMessage(
      id: _uuid.v4(),
      text: userText,
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
      userQuestion: userText,
    ));
    notifyListeners();

    try {
      final buffer = StringBuffer();
      List<RetrievedContextPreview> contexts = const [];
      String? retrievalMode;
      final useRemote = _useRemoteRag && ApiConfig.isRemoteConfigured;
      if (kDebugMode) {
        debugPrint(
          '[ChatProvider] useRemoteRag=$_useRemoteRag '
          'apiConfigured=${ApiConfig.isRemoteConfigured} → stream=${useRemote ? "remote" : "local"}',
        );
      }

      if (useRemote) {
        await for (final ev in _remoteRag.queryStreamEvents(
          userText,
          docId: _activeDocId,
        )) {
          switch (ev.kind) {
            case RagStreamEventKind.meta:
              contexts = ev.meta?.contexts ?? const [];
              retrievalMode = ev.meta?.retrievalMode;
              _updateAiMessage(
                aiMsgId,
                buffer.toString(),
                MessageStatus.sending,
                retrievedContexts: contexts,
                retrievalMode: retrievalMode,
              );
            case RagStreamEventKind.text:
              buffer.write(ev.text ?? '');
              _updateAiMessage(
                aiMsgId,
                buffer.toString(),
                MessageStatus.sending,
                retrievedContexts: contexts,
                retrievalMode: retrievalMode,
              );
            case RagStreamEventKind.error:
              _updateAiMessage(
                aiMsgId,
                ev.text ?? 'Lỗi không xác định',
                MessageStatus.error,
              );
              _isThinking = false;
              notifyListeners();
              return;
            case RagStreamEventKind.done:
              break;
          }
        }
      } else {
        await for (final chunk in _localRag.queryStream(userText, docId: _activeDocId)) {
          buffer.write(chunk);
          _updateAiMessage(aiMsgId, buffer.toString(), MessageStatus.sending);
        }
      }

      _updateAiMessage(
        aiMsgId,
        buffer.toString(),
        MessageStatus.done,
        retrievedContexts: contexts,
        retrievalMode: retrievalMode,
      );
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

  void _updateAiMessage(
    String id,
    String text,
    MessageStatus status, {
    List<RetrievedContextPreview>? retrievedContexts,
    String? retrievalMode,
  }) {
    final idx = _messages.indexWhere((m) => m.id == id);
    if (idx < 0) return;
    _messages[idx] = _messages[idx].copyWith(
      text: text,
      status: status,
      retrievedContexts: retrievedContexts,
      retrievalMode: retrievalMode,
    );
    notifyListeners();
  }

  Future<void> rateRagMessage(String messageId, RagMessageRating rating) async {
    final idx = _messages.indexWhere((m) => m.id == messageId);
    if (idx < 0) return;
    final msg = _messages[idx];
    if (!msg.isAI || msg.status != MessageStatus.done) return;

    _messages[idx] = msg.copyWith(ragRating: rating);
    notifyListeners();

    final ok = await RagFeedbackService.instance.submit(
      messageId: msg.id,
      question: msg.userQuestion ?? '',
      answer: msg.text,
      rating: rating,
      contexts: msg.retrievedContexts,
      retrievalMode: msg.retrievalMode,
    );
    if (!ok && kDebugMode) {
      debugPrint('[ChatProvider] rag feedback not persisted');
    }
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
