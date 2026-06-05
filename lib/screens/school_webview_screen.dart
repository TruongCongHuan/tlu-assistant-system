// lib/screens/school_webview_screen.dart
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../theme/app_theme.dart';
import '../widgets/notification_bell_button.dart';

/// UA giống Chrome mobile thật — không dùng chuỗi mặc định có `; wv)` (WebView),
/// giúp một số site trường và giảm lỗi `ERR_BLOCKED_BY_ORB` trên Android WebView.
const _kChromeMobileUserAgent =
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36';

class SchoolWebViewScreen extends StatefulWidget {
  final String title;
  final String initialUrl;

  const SchoolWebViewScreen({
    super.key,
    required this.title,
    required this.initialUrl,
  });

  @override
  State<SchoolWebViewScreen> createState() => _SchoolWebViewScreenState();
}

class _SchoolWebViewScreenState extends State<SchoolWebViewScreen> {
  WebViewController? _controller;
  var _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _prepareController();
  }

  Future<void> _prepareController() async {
    final uri = Uri.tryParse(widget.initialUrl);
    if (uri == null || !uri.hasScheme) {
      if (mounted) {
        setState(() {
          _error = 'URL không hợp lệ';
          _loading = false;
        });
      }
      return;
    }

    final controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(AppTheme.background)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (mounted) {
              setState(() {
                _loading = true;
                _error = null;
              });
            }
          },
          onPageFinished: (_) {
            if (mounted) setState(() => _loading = false);
          },
          onWebResourceError: (err) {
            // Chỉ báo lỗi khung chính — tránh ORB ở tài nguyên phụ làm tắt cả trang.
            if (err.isForMainFrame == false) return;
            if (mounted) {
              setState(() {
                _loading = false;
                _error = err.description;
              });
            }
          },
        ),
      );

    try {
      await controller.setUserAgent(_kChromeMobileUserAgent);
      await controller.loadRequest(uri);
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString();
        });
      }
      return;
    }

    if (!mounted) return;
    setState(() => _controller = controller);
  }

  Future<void> _openInExternalBrowser() async {
    final u = Uri.tryParse(widget.initialUrl);
    if (u == null) return;
    try {
      await launchUrl(u, mode: LaunchMode.externalApplication);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Không mở được trình duyệt ngoài.'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final orbHint = _error != null &&
        _error!.toUpperCase().contains('ORB');

    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(color: AppTheme.textPrimary),
        title: Text(widget.title),
        actions: [
          IconButton(
            icon: const Icon(Icons.open_in_new_rounded,
                color: AppTheme.textSecondary),
            tooltip: 'Mở trong trình duyệt',
            onPressed: _openInExternalBrowser,
          ),
          const NotificationBellButton(),
        ],
      ),
      body: Stack(
        children: [
          if (_error != null)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.wifi_tethering_error_rounded,
                        size: 48, color: AppTheme.textTertiary.withOpacity(0.8)),
                    const SizedBox(height: 16),
                    Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: AppTheme.textSecondary),
                    ),
                    if (orbHint) ...[
                      const SizedBox(height: 12),
                      const Text(
                        'Một số trang trường chặn hiển thị trong WebView (ORB). '
                        'Hãy mở bằng Chrome / Safari bên ngoài.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: AppTheme.textTertiary,
                          fontSize: 13,
                          height: 1.4,
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                    FilledButton.icon(
                      onPressed: _openInExternalBrowser,
                      icon: const Icon(Icons.open_in_browser_rounded, size: 20),
                      label: const Text('Mở trong trình duyệt'),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppTheme.accent,
                        foregroundColor: AppTheme.background,
                      ),
                    ),
                  ],
                ),
              ),
            )
          else if (_controller != null)
            WebViewWidget(controller: _controller!)
          else
            const Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppTheme.accent,
              ),
            ),
          if (_loading && _error == null && _controller != null)
            const LinearProgressIndicator(
              minHeight: 2,
              color: AppTheme.accent,
              backgroundColor: AppTheme.surfaceHigh,
            ),
        ],
      ),
    );
  }
}
