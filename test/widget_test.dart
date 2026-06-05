import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('smoke: MaterialApp builds', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(child: Text('TLU AI')),
        ),
      ),
    );
    expect(find.text('TLU AI'), findsOneWidget);
  });
}
