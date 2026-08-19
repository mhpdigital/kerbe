import 'package:flutter/material.dart';

/// Detail screen for a gallery item (plan task T3).
/// Built, but no route registers it — nothing can reach this screen.
class GalleryDetailScreen extends StatelessWidget {
  const GalleryDetailScreen({super.key, this.itemId = 0});

  final int itemId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Item $itemId')),
      body: Center(child: Text('Detail for item $itemId')),
    );
  }
}
