// Pin untuk motor dan encoder
const int enA = 9;          // Pin PWM untuk kecepatan motor
const int in1 = 7;          // Pin arah Counter Clockwise
const int in2 = 8;          // Pin arah Clockwise
const int encoderPin = 2;   // Pin untuk membaca pulsa dari encoder

// Konstanta
const int PPR = 11;         // Pulsa per rotasi encoder 
const unsigned long interval = 100; // Interval waktu untuk menghitung RPM (100 ms)


// Variabel global
volatile int pulseCount = 0;      // Menghitung pulsa encoder (gunakan volatile untuk interrupt)
int pwmValue = 0;                 // Nilai PWM untuk mengatur kecepatan motor
unsigned long previousMillis = 0; // Waktu sebelumnya untuk interval
float rpm = 0;                    // Menyimpan nilai RPM
bool motorRunning = false;        // Status motor aktif
float kp = 1.0;        // Koefisien Proportional
float ki = 0.5;        // Koefisien Integral
float kd = 0.1;       // Koefisien Derivative
float setpoint = 100;  // Kecepatan yang diinginkan (RPM target) - ini dapat diubah melalui input
float Error = 0;       // Error antara setpoint dan nilai RPM saat ini
float prevError = 0;   // Error sebelumnya
float integralError = 0; // Integral error
float derivativeError = 0; // Derivative error
float pidValue = 0;     // Nilai output PID
int maxPWM = 255;       // Nilai PWM maksimum yang dapat diberikan ke motor

// Fungsi untuk PID
int PIDControl() {
    float PControl, IControl, DControl, POutput; // Deklarasi Variabel PID
    Error = setpoint - rpm; // Menghitung Nilai Error
    PControl = kp * Error; // Menghitung Nilai Proporsional
    integralError += Error; // Menghitung Error Kumulatif(Integral)
    IControl = ki * integralError; // Menghitung Nilai Integral
    DControl = kd * derivativeError; // Menghitung Nilai Derivatif
    derivativeError = Error - prevError; // Menghitung Laju Perubahan Error
    prevError = Error; // Menyimpan Error Saat ini untuk iterasi selanjutnya
    POutput = PControl + IControl + DControl; // Menghitung Nilai Total output PID
    pidValue = constrain(POutput, 0, maxPWM); // Membatasi Output PID dalam rentang nilai yang Valid
    return pidValue; 
}
void setup(){
  // Konfigurasi pin
  pinMode(enA, OUTPUT);      // Output PWM
  pinMode(in1, OUTPUT);      // Output arah motor
  pinMode(in2, OUTPUT);      // Output arah motor
  pinMode(encoderPin, INPUT);// Input encoder
  attachInterrupt(digitalPinToInterrupt(encoderPin), countPulse, RISING); // Interrupt untuk encoder

  Serial.begin(9600);        // Inisialisasi komunikasi serial
}

// Fungsi interrupt untuk menghitung pulsa encoder
void countPulse() {
  pulseCount++;
}
// Fungsi untuk Arah Putar Motor CCW
void motorReverse() {
  digitalWrite(in1, HIGH); // Mengatur pin in1 dengan logika 1
  digitalWrite(in2, LOW); // Mengatur pin in2 dengan logika 0
  motorRunning = true; // Mengubah status motor
  Serial.println("Motor bergerak ke arah Counter Clockwise.");
}
// Fungsi untuk Arah Putar Motor CW
void motorForward() {
  digitalWrite(in1, LOW); // Mengatur pin in1 dengan logika 0
  digitalWrite(in2, HIGH); // Mengatur pin in2 dengan logika 1
  motorRunning = true; // Mengubah status motor
  Serial.println("Motor bergerak ke arah Clockwise.");
}
// Fungsi untuk menghentikan motor
void motorStop() {
  digitalWrite(in1, LOW); // Mengatur pin in1 dengan logika 0
  digitalWrite(in2, LOW); // Mengatur pin in2 dengan logika 0
  analogWrite(enA, 0); // Memastikan nilai PWM untuk enA 0
  motorRunning = false; // Mengubah status motor
  Serial.println("Motor berhenti.");
}
void loop() {
  // Cek apakah ada data masuk dari Serial Monitor
  if (Serial.available() > 0) {
    String input = Serial.readString();
    processInput(input); // Proses input
  }
  // Hitung RPM setiap interval waktu
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis; // Reset waktu

    // Hitung RPM
    calculateRPM();

     // Jika motor berjalan, gunakan PID untuk mengatur PWM
    if (motorRunning) {
      pwmValue = PIDControl();  // Hitung nilai PWM menggunakan PID
      analogWrite(enA, pwmValue); // Terapkan nilai PWM ke motor

      // Kirim data melalui serial
      Serial.print("DATA:");
      Serial.print(currentMillis / 1000.0); // Waktu dalam detik
      Serial.print(",");
      Serial.print(rpm);
      Serial.print(",");
      Serial.println(setpoint);
       if (Serial.available() > 0) {
        String input = Serial.readStringUntil('\n');
        processInput(input);} // Proses input
    }
  }
}
// Fungsi Untuk Perintah Input
void processInput(String input) {
  input.trim();           // Hapus spasi atau karakter kosong
  input.toUpperCase();    // Ubah ke huruf besar agar case-insensitive

  if (input.startsWith("F")) { // Perintah untuk arah Clockwisse
    setpoint = input.substring(1).toFloat(); // Ambil nilai setelah "F"
    if (setpoint >= 0) {
      Serial.print("Setpoint RPM (Clockwise) diatur ke: ");
      Serial.println(setpoint);
      // Aktifkan motor arah Clockwise jika setpoint > 0
      if (setpoint > 0) {
        motorForward(); // Fungsi motor arah Clockwise
      }
    } else {
      Serial.println("Nilai RPM tidak valid.");
    }

  } else if (input.startsWith("R")) { // Perintah untuk arah Counter Clockwise
    setpoint = input.substring(1).toFloat(); // Ambil nilai setelah "R"
    if (setpoint >= 0) {
      Serial.print("Setpoint RPM (Counter CLockwise) diatur ke: ");
      Serial.println(setpoint);

      // Aktifkan motor mundur jika setpoint > 0
      if (setpoint > 0) {
        motorReverse(); // Fungsi motor arah Counter Clockwise
      }
    } else {
      Serial.println("Nilai RPM tidak valid.");
    }

  } else if (input == "STOP") { // Perintah berhenti
    motorStop();
    setpoint = 0; // Reset setpoint
    Serial.println("Motor berhenti.");

  }  else if (input.startsWith("PID,")) {
    // Memproses input PID
    String pidValues = input.substring(4); //  Mengambil substring setelah karakter ke-4 dari input (yaitu, setelah PID,)
    int firstComma = pidValues.indexOf(','); // Mencari posisi koma pertama dalam string pidValue
    int secondComma = pidValues.indexOf(',', firstComma + 1); // Mencari posisi koma kedua dalam string pidValue
    if (firstComma > 0 && secondComma > firstComma) { // Mengecek apakah koma ditemukan dalam urutan yang benar
      String kpStr = pidValues.substring(0, firstComma); // Mengambil nilai Kp sebagai substring sebelum koma pertama
      String kiStr = pidValues.substring(firstComma + 1, secondComma); // Mengambil nilai Ki sebagai substring diantara koma pertama dan kedua
      String kdStr = pidValues.substring(secondComma + 1); // Mengambil nilai Kd sebagai substring setelah koma kedua

      float newKp = kpStr.toFloat(); // Mengonversi string kpStr menjadi nilai floating-point newKp
      float newKi = kiStr.toFloat(); // Mengonversi string kiStr menjadi nilai floating-point newKi
      float newKd = kdStr.toFloat(); // Mengonversi string kdStr menjadi nilai floating-point newKd

      //  Mengupdate nilai kp, ki, dan kd dengan nilai baru yang diberikan dari input serial
      kp = newKp;
      ki = newKi;
      kd = newKd;

      Serial.print("Updated PID parameters: kp=");
      Serial.print(kp);
      Serial.print(", ki=");
      Serial.print(ki);
      Serial.print(", kd=");
      Serial.println(kd);
    } else {
      Serial.println("Invalid PID parameters");
    }
  } else {
    Serial.println("Perintah tidak dikenal. Gunakan 'F[rpm]' untuk maju, 'R[rpm]' untuk mundur, 'PID,kp,ki,kd' untuk mengatur PID, atau 'STOP'.");
  }
}
// Fungsi untuk menghitung RPM
void calculateRPM() {
  rpm = ((pulseCount / (float)PPR) / 9.6) * 600.0; // RPM = (Pulsa / Pulsa per rotasi) x 60 detik
  pulseCount = 0; // Reset hitungan pulsa
}