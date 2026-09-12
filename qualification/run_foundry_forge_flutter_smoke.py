#!/usr/bin/env python3
"""Public, source-free Flutter dependency/toolchain smoke for FORGE client work.

This script intentionally contains no MUSITU product source, schemas, endpoints,
keys, customer data, or private artifacts. It exercises only public Flutter
packages and generic platform compilation.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

FLUTTER = "flutter.bat" if os.name == "nt" else "flutter"

PUBSPEC = r'''name: universal_toolchain_smoke
description: Public generic cross-platform Flutter dependency smoke.
publish_to: none
version: 0.0.1+1

environment:
  sdk: ">=3.12.0 <4.0.0"
  flutter: ">=3.47.0"

dependencies:
  flutter:
    sdk: flutter
  camera: 0.12.1
  connectivity_plus: 7.3.1
  crypto: 3.0.7
  cryptography: 2.9.0
  file_selector: 1.1.0
  flutter_secure_storage: 11.1.1
  http: 1.6.0
  image: 4.9.2
  path_provider: 2.1.6
  sembast: 3.8.10
  sembast_web: 2.4.5+1

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: 6.0.0

flutter:
  uses-material-design: true
'''

MAIN = r'''import 'dart:convert';

import 'package:camera/camera.dart' as camera;
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:cryptography/cryptography.dart';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as image;
import 'package:path_provider/path_provider.dart';

import 'db.dart';

Future<void> publicDependencyProbe() async {
  final cipher = AesGcm.with256bits();
  final key = await cipher.newSecretKey();
  final box = await cipher.encrypt(utf8.encode('smoke'), secretKey: key);
  final clear = await cipher.decrypt(box, secretKey: key);
  if (clear.isEmpty) throw StateError('aes-gcm probe failed');

  const secureStorage = FlutterSecureStorage();
  if (secureStorage.hashCode == -1) throw StateError('unreachable');

  final client = http.Client();
  client.close();

  final connectivity = Connectivity();
  if (connectivity.hashCode == -1) throw StateError('unreachable');

  const mediaType = XTypeGroup(label: 'media', extensions: ['jpg']);
  if ((mediaType.label ?? '').isEmpty) throw StateError('file selector probe failed');

  final generated = image.Image(width: 2, height: 2)
    ..clear(image.ColorRgb8(255, 255, 255));
  final encoded = image.encodeJpg(generated);
  if (encoded.isEmpty) throw StateError('image encode probe failed');

  final cameraFunction = camera.availableCameras;
  final supportDirectoryFunction = getApplicationSupportDirectory;
  if (cameraFunction.hashCode == -1 || supportDirectoryFunction.hashCode == -1) {
    throw StateError('unreachable');
  }

  final marker = databaseFactoryMarker();
  if (marker.hashCode == -1) throw StateError('unreachable');
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await publicDependencyProbe();
  runApp(const MaterialApp(home: Scaffold(body: Text('public toolchain smoke'))));
}
'''

DB = r'''import 'db_stub.dart'
    if (dart.library.io) 'db_io.dart'
    if (dart.library.js_interop) 'db_web.dart' as platform;

Object databaseFactoryMarker() => platform.databaseFactoryMarker();
'''

DB_IO = r'''import 'package:sembast/sembast_io.dart';

Object databaseFactoryMarker() => databaseFactoryIo;
'''

DB_WEB = r'''import 'package:sembast_web/sembast_web.dart';

Object databaseFactoryMarker() => databaseFactoryWeb;
'''

DB_STUB = r'''Object databaseFactoryMarker() => 'unsupported';
'''

TEST = r'''import 'package:cryptography/cryptography.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as image;

void main() {
  test('AES-GCM and image dependencies are available', () {
    expect(AesGcm.with256bits().nonceLength, greaterThan(0));
    final generated = image.Image(width: 1, height: 1)
      ..clear(image.ColorRgb8(0, 0, 0));
    expect(image.encodeJpg(generated), isNotEmpty);
  });
}
'''


def run(*args: str, cwd: Path) -> None:
    print('+', ' '.join(args), flush=True)
    subprocess.run(args, cwd=cwd, check=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--target',
        required=True,
        choices=['web', 'android', 'linux', 'windows', 'macos', 'ios'],
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix='forge-flutter-smoke-') as tmp:
        root = Path(tmp)
        platform = 'android' if args.target == 'android' else args.target
        run(
            FLUTTER,
            'create',
            '--org',
            'dev.musitu.publicsmoke',
            '--project-name',
            'universal_toolchain_smoke',
            f'--platforms={platform}',
            '.',
            cwd=root,
        )
        write(root / 'pubspec.yaml', PUBSPEC)
        write(root / 'lib' / 'main.dart', MAIN)
        write(root / 'lib' / 'db.dart', DB)
        write(root / 'lib' / 'db_io.dart', DB_IO)
        write(root / 'lib' / 'db_web.dart', DB_WEB)
        write(root / 'lib' / 'db_stub.dart', DB_STUB)
        shutil.rmtree(root / 'test', ignore_errors=True)
        write(root / 'test' / 'dependency_smoke_test.dart', TEST)

        run(FLUTTER, 'pub', 'get', cwd=root)
        run(FLUTTER, 'analyze', '--no-fatal-infos', cwd=root)
        run(FLUTTER, 'test', cwd=root)

        commands = {
            'web': (FLUTTER, 'build', 'web'),
            'android': (FLUTTER, 'build', 'apk', '--debug'),
            'linux': (FLUTTER, 'build', 'linux', '--debug'),
            'windows': (FLUTTER, 'build', 'windows', '--debug'),
            'macos': (FLUTTER, 'build', 'macos', '--debug'),
            'ios': (FLUTTER, 'build', 'ios', '--simulator', '--debug'),
        }
        run(*commands[args.target], cwd=root)
        print(f'PUBLIC_TOOLCHAIN_SMOKE_PASS target={args.target}', flush=True)


if __name__ == '__main__':
    main()
