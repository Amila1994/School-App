plugins {
    id("com.android.application")
}

android {
    namespace = "com.example.schoolapp"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.schoolapp"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }
}

dependencies {
    implementation("androidx.appcompat:appcompat:1.6.1")
}
