/// Formats a byte count for display. (No caller — fixture decoy D1.)
String formatBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  return '${(bytes / 1024).toStringAsFixed(1)} KB';
}
