# Artifacts - שאלות ותשובות

**שאלה 1:** איך מנוהלים ה-artifacts בפרויקט ומה התוכן של BSP deployment manifest?

**תשובה:** ה-artifacts מנוהלים דרך NFS/JFrog Artifactory ו-BSP deployment manifests (כמו `bsp-main-137.yaml`). ה-manifest כולל:
- **Build Information** - Build ID, commit hash וversion tracking
- **Artifact Details** - רשימת artifacts מלאה עם checksums ומיקומי הורדה
- **Deployment Configuration** - הגדרות provisioning חומרה ושיטות deployment
- **Runtime Configuration** - הגדרות רשת, console ומערכת
- **Test Plan** - חבילות בדיקה ספציפיות להרצה עבור build זה
המערכת מורידה ומאמתת build artifacts אוטומטית, מגדירה את ה-DUT לפי specifications ב-manifest, ומריצה test suites מוגדרים תוך קישור תוצאות חזרה ל-build ו-commit המדויקים.

**שאלה 2:** איך מתבצעת הורדה ואימות של artifacts?

**תשובה:** הורדת artifacts מתבצעת ב-`_download_artifact` method:
- הורדה מ-URL באמצעות requests library עם streaming
- שמירה לקובץ זמני עם suffix מתאים
- בדיקת checksums מול הערכים ב-manifest
- Timeout של 300 שניות להורדות גדולות
- Error handling עם retry logic
- Cleanup אוטומטי של קבצים זמניים בכישלון

**שאלה 3:** איך מוגדרת retention policy ל-artifacts?

**תשובה:** Retention policy מוגדרת במשתני סביבה:
- `ARTIFACT_RETENTION_DAYS=30` - שמירה של 30 יום
- Cleanup אוטומטי של artifacts ישנים
- Archive של test results לתקופה ארוכה יותר
- Backup ל-cloud storage לartifacts קריטיים
- Version tracking עם build IDs לtraceability
- Compression של artifacts ישנים לחיסכון במקום

**שאלה 4:** איך מתבצע firmware flashing מ-artifacts?

**תשובה:** Firmware flashing מתבצע ב-`_flash_firmware`:
- הורדת bootloader ו-FPGA bitstream מ-manifest
- שימוש ב-JTAG controller לflashing
- Flash של bootloader ל-boot target
- Flash של FPGA bitstream ל-fpga target
- בדיקת success/failure עם error messages מפורטים
- Logging של כל שלב לtraceability

**שאלה 5:** איך מנוהלים artifact repositories (NFS vs Artifactory)?

**תשובה:** המערכת תומכת במספר artifact sources:
- **NFS**: mount ל-/mnt/nfs_artifacts עם direct file access
- **Artifactory**: HTTP-based downloads עם authentication
- Auto-detection של source type לפי URL format
- Fallback mechanisms בין sources
- Caching מקומי לביצועים טובים יותר
- Network resilience עם retry logic

**שאלה 6:** איך מתבצע version tracking של artifacts?

**תשובה:** Version tracking כולל:
- Build ID ייחודי לכל artifact set
- Commit hash קישור לsource code
- Timestamp של build creation
- Manifest version לbackward compatibility
- Component versions לכל artifact בנפרד
- Dependency tracking בין artifacts
- Change log עם release notes

**שאלה 7:** איך מטופלים artifact dependencies?

**תשובה:** Dependencies מנוהלים דרך manifest structure:
- רשימת components עם version constraints
- Dependency resolution לפני הורדה
- Validation של compatibility בין components
- Error reporting על missing dependencies
- Automatic download של required dependencies
- Conflict resolution עם version priorities

**שאלה 8:** איך מתבצע artifact validation לפני שימוש?

**תשובה:** Validation כולל מספר שלבים:
- MD5/SHA checksum verification
- File size validation
- Format validation (ELF, bitstream, etc.)
- Digital signature verification אם זמין
- Compatibility check עם target board
- Virus scanning אם מוגדר
- Quarantine של artifacts חשודים

**שאלה 9:** איך מנוהלים test artifacts ותוצאות?

**תשובה:** Test artifacts כוללים:
- JUnit XML reports מ-pytest
- HTML test reports עם screenshots
- Log files מ-test execution
- Performance metrics ו-timing data
- Hardware state dumps
- Error screenshots ו-debug info
- כל הקבצים מארכבים ב-Jenkins עם build number

**שאלה 10:** איך מתבצע cleanup ו-storage management של artifacts?

**תשובה:** Storage management כולל:
- Automated cleanup של artifacts ישנים לפי retention policy
- Compression של archived artifacts
- Tiered storage - hot/warm/cold
- Monitoring של disk usage עם alerts
- Backup ל-cloud storage לlong-term retention
- Deduplication של identical artifacts
- Cleanup של temporary files אחרי test completion
