import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screens/cockpit_screen.dart';
import 'theme/apple_cupertino_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Configurar modo imersivo de direção (tela cheia e sem barra de status)
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);
  runApp(const GalvaoLogiApp());
}

class GalvaoLogiApp extends StatelessWidget {
  const GalvaoLogiApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Galvão Logi',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: AppleTokens.deepSpaceBlack,
        fontFamily: 'SF Pro Display',
      ),
      home: const CockpitScreen(),
    );
  }
}
