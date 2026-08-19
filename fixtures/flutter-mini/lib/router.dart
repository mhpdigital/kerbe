import 'package:go_router/go_router.dart';
import 'screens/gallery_screen.dart';

final router = GoRouter(
  routes: [
    GoRoute(path: '/', redirect: (context, state) => '/gallery'),
    GoRoute(path: '/gallery', builder: (context, state) => const GalleryScreen()),
  ],
);
