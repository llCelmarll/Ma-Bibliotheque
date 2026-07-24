const { version } = require("react");

const isStaging = process.env.APP_VARIANT === "staging";

module.exports = {
  expo: {
    name: isStaging ? "Bibliothèque STAGING" : "Bibliothèque",
    slug: "bibliotheque", // Identifiant unique pour Expo
    version: "1.0.8", // Version de l'application
    orientation: "portrait", // Orientation par défaut
    icon: isStaging ? "./assets/icon-staging.png" : "./assets/icon.png",
    splash: {
      image: "./assets/splash.png", // Image de démarrage (à ajouter)
      resizeMode: "contain",
      backgroundColor: "#ffffff"
    },
    extra: {
      apiUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000',
      eas: {
        projectId: "b94a31f7-30e7-4781-8a4d-c32e75cb7e82"
      }
    },
    updates: {
      url: "https://u.expo.dev/b94a31f7-30e7-4781-8a4d-c32e75cb7e82",
      fallbackToCacheTimeout: 0,
      enabled: false,
    },
    runtimeVersion: "stable",
    assetBundlePatterns: [
      "**/*" // Pattern pour inclure tous les assets
    ],
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.lcelmarl.bibliotheque.frontend"
    },
    android: {
      package: isStaging ? "com.lcelmarl.bibliotheque.frontend.staging" : "com.lcelmarl.bibliotheque.frontend",
      googleServicesFile: "./google-services.json",
      usesCleartextTraffic: true,
      adaptiveIcon: {
        foregroundImage: isStaging ? "./assets/adaptive-icon-staging.png" : "./assets/adaptive-icon.png",
        backgroundColor: "#FFFFFF"
      },
      permissions: [
        "CAMERA",
        "POST_NOTIFICATIONS"
      ]
    },
    web: {
      favicon: "./assets/favicon.png", // Favicon pour la version web (à ajouter)
      camera: {
        enableBarCode: true,
        enableQrCode: true,
        enableFrontCamera: true,
        enableBackCamera: true,

      }
    },
    plugins: [
      [
        "expo-camera",
        {
          "cameraPermissions": "Autorisez l'accès à la caméra pour scanner les livres",
        }
      ],
      [
        "expo-image-picker",
        {
          "photosPermission": "Autorisez l'accès à vos photos pour choisir une couverture de livre",
          "cameraPermission": "Autorisez l'accès à la caméra pour prendre une photo de couverture"
        }
      ],
      "expo-router",
      "expo-web-browser",
      "expo-secure-store",
      [
        "expo-notifications",
        {
          "icon": "./assets/adaptive-icon.png",
          "color": "#ffffff",
          "defaultChannel": "default",
          "sounds": []
        }
      ]
    ]
  }
};
