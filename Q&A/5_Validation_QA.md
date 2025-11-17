# Validation - שאלות ותשובות

**שאלה 1:** מה כולל תהליך הולידציה של ZCU102 BSP ואיך מוגדרים קריטריוני הקבלה?

**תשובה:** תהליך הולידציה כולל מספר תחומים עיקריים:
- **Boot Sequence** - בדיקת תקינות, ביצועים ואמינות לאורך מחזורי הפעלה
- **Protocol Testing** - בדיקת UART, Ethernet ותקשורת פונקציונלית
- **Linux System** - בדיקת ביצועים, מאפיינים real-time ויציבות
- **Security Hardening** - בדיקת קונפיגורציה ועמידה בתקנים
קריטריוני הקבלה מוגדרים ב-`config.yaml` תחת `acceptance_criteria`, כולל זמן boot מקסימלי (45 שניות), הודעות boot נדרשות ("U-Boot 202", "Linux version", "login:") והודעות אסורות ("kernel panic").

**שאלה 2:** איך מתבצעת בדיקת Boot Sequence ומה הקריטריונים לבדיקה?

**תשובה:** בדיקת Boot Sequence מתבצעת דרך `BootValidator` class שמתחבר לserial console ומנטר את תהליך האתחול. הבדיקה כוללת:
- זמן boot מקסימלי של 45 שניות
- זיהוי הודעות boot חובה: "U-Boot 202", "Linux version", "login:"
- וידוא שאין הודעות שגיאה כמו "kernel panic"
- בדיקת יציבות לאורך מחזורי power cycle מרובים
- מדידת ביצועי boot וזיהוי degradation לאורך זמן

**שאלה 3:** איך מתבצעת בדיקת UART ומה נבדק?

**תשובה:** בדיקת UART מתבצעת דרך `UartTester` class עם חיבור serial. הבדיקות כוללות:
- בדיקת תקשורת בסיסית - שליחה וקבלה של נתונים
- בדיקת baud rates שונים (115200 ברירת מחדל)
- בדיקת flow control ו-parity settings
- בדיקות ביצועים - throughput ו-latency
- בדיקת error handling ו-recovery מכישלוני תקשורת
- בדיקת buffer overflow ו-underflow scenarios

**שאלה 4:** איך מתבצעת בדיקת Ethernet ורשת?

**תשובה:** בדיקת Ethernet מתבצעת דרך `EthernetTester` עם הגדרות רשת מ-`config.yaml`:
- בדיקת קישוריות בסיסית - ping ל-gateway (192.168.1.1)
- בדיקת הגדרות IP סטטיות (target: 192.168.1.100, test host: 192.168.1.10)
- בדיקות ביצועים - throughput, latency, packet loss
- בדיקת MTU sizes שונים
- בדיקות stress - high traffic loads
- בדיקת network recovery אחרי disconnection

**שאלה 5:** איך מוגדרים ומתבצעים test suites שונים?

**תשובה:** Test suites מוגדרים ב-`config.yaml` תחת `test_suites`:
- **smoke** (15 דק') - boot_sequence, uart_basic, network_ping
- **regression** (60 דק') - כל הבדיקות הבסיסיות + gpio_loopback, i2c_device_scan, system_stability
- **full** (240 דק') - כל הבדיקות + spi_device_test, system_stress, power_cycle_endurance
כל suite כולל timeout גלובלי ורשימת בדיקות ספציפיות.

**שאלה 6:** איך מתבצעת בדיקת GPIO ו-I2C?

**תשובה:** בדיקות GPIO ו-I2C מתבצעות דרך hardware control interfaces:
- **GPIO**: בדיקות loopback בין pins, בדיקת input/output modes, בדיקת interrupt handling
- **I2C**: סריקת devices על הbus, בדיקת תקשורת עם peripherals ידועים, בדיקת clock stretching ו-error conditions
- שתי הבדיקות דורשות hardware fixtures מתאימים במעבדה
- התוצאות מתועדות עם פרטי timing ו-signal integrity

**שאלה 7:** איך מתבצעות בדיקות יציבות ו-stress?

**תשובה:** בדיקות יציבות כוללות:
- **System Stability**: הרצה ממושכת עם monitoring של CPU, memory, temperature
- **System Stress**: עומסים גבוהים על CPU, memory, I/O ו-network בו-זמנית
- **Power Cycle Endurance**: מחזורי הפעלה/כיבוי מרובים עם בדיקת boot אחרי כל מחזור
- כל בדיקה כוללת thresholds מוגדרים לביצועים ויציבות
- התוצאות מנותחות לזיהוי trends ו-degradation

**שאלה 8:** איך מתבצע hardware provisioning לפני בדיקות?

**תשובה:** Hardware provisioning מתבצע ב-`TestOrchestrator.provision_hardware()`:
- Power cycle של הלוח למצב נקי
- הורדת firmware artifacts מ-BSP manifest
- Flashing של bootloader ו-FPGA bitstream דרך JTAG
- המתנה לboot completion ו-system ready state
- אימות שהמערכת מגיבה לפקודות
- כל השלבים מתועדים עם timestamps ו-success indicators

**שאלה 9:** איך מתבצע דיווח ותיעוד תוצאות validation?

**תשובה:** דיווח תוצאות מתבצע במספר רמות:
- **Real-time**: logs ל-ELK Stack עם structured data
- **Metrics**: Prometheus metrics עם timestamps ו-performance data
- **Reports**: HTML ו-JUnit XML reports מ-pytest
- **Final Report**: comprehensive report עם session ID, build info, hardware status, test results
- **Notifications**: Slack ו-email עם סיכום תוצאות
- כל הדיווחים קשורים ל-test session ID ו-build version לtraceability

**שאלה 10:** איך מתבצעת validation של BSP manifests ו-artifacts?

**תשובה:** Validation של BSP manifests כוללת:
- פרסור ואימות מבנה ה-manifest (required fields, format)
- בדיקת checksums של artifacts מול הערכים ב-manifest
- אימות שכל ה-artifacts הנדרשים זמינים ב-repository
- בדיקת compatibility בין board type ב-manifest לקונפיגורציה
- אימות שה-test plan ב-manifest תואם ל-available test suites
- כל שגיאת validation מתועדת ומונעת המשך הרצה
