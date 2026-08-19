import 'package:flutter/material.dart';

class GalleryScreen extends StatelessWidget {
  const GalleryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: Image.asset('images/logo.png'),
        title: const Text('Gallery'),
      ),
      body: GridView.count(
        crossAxisCount: 3,
        children: List.generate(
          9,
          (i) => Card(child: Center(child: Text('Item $i'))),
        ),
      ),
    );
  }
}
