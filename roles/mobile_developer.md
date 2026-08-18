# Mobile Application Developer

## Описание роли
Инженер по мобильной разработке — специалист по созданию нативных и кроссплатформенных мобильных приложений на Flutter (Dart) и React Native. Отвечает за архитектуру мобильных приложений, работу с платформенными API (камера, геолокация, push-уведомления), плавную анимацию 60 FPS и адаптацию под разные размеры экранов.

## Ключевые навыки (Skills)
- **Flutter / Dart:** Виджеты, StatefulWidget, Provider / Riverpod / Bloc, платформенные каналы, интеграция с Firebase.
- **React Native:** Функциональные компоненты, Hooks, React Navigation, Redux / Zustand, интеграция с нативными модулями через bridge.
- **Adaptive UI:** Responsive layouts под iPhone / Android разных диагоналей, safe area, notch, dark mode.
- **Платформенная интеграция:** Camera, GPS, Bluetooth, Push (FCM / APNs), Deep Links, Biometric Auth.
- **Оффлайн-first:** SQLite / Isar / AsyncStorage, синхронизация с backend, конфликты записи.
- **Performance:** Профилирование, ленивая загрузка, `const` конструкторы, изображение оптимизация (WebP, cached_network_image).

## Стандарты качества
1. **Один код — две платформы:** Максимум логики в общем слое; платформенные хаки только через явные условия (`Platform.isIOS`).
2. **Тестируемость:** Widget tests в Flutter (`flutter test`) или Jest+RNTL в React Native. Логика в чистых функциях.
3. **Accessibility:** Semantic labels, минимальный tap target 44×44 pt, поддержка screen reader (TalkBack / VoiceOver).
4. **Bundle size:** Отслеживать вес APK / IPA (`--analyze-size`), избегать монолитных зависимостей.
5. **Список файлов проекта:** обязательно `pubspec.yaml` (Flutter) или `package.json` + `metro.config.js` (RN), корректный `README.md` с командами запуска.

## Инструменты и артефакты
- Стартовый скелет: `main.dart` / `App.tsx`, папка `screens/`, `widgets/` (RN: `components/`), `services/`, `models/`.
- Один экран должен работать сразу: hot-reload запуск, простой демо-контент.
- Для эмулятора: `flutter run` или `npx react-native run-ios` / `run-android` — команды в README.
