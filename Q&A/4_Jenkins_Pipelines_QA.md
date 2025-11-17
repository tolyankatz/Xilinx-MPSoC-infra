# Jenkins & Pipelines - שאלות ותשובות

**שאלה 1:** איך מוגדר Jenkins pipeline בפרויקט ומה הפרמטרים העיקריים שהוא מקבל?

**תשובה:** ה-pipeline מוגדר ב-`Jenkinsfile` ומופעל על ידי filesystem monitoring או הרצה ידנית. הפרמטרים העיקריים:
- `MANIFEST_PATH` - נתיב ל-BSP manifest file על NFS share
- `BUILD_ID` - מזהה build מה-manifest
- `NFS_BUILD_PATH` - נתיב מלא ל-build directory עם artifacts
- `TEST_SCOPE` - היקף הבדיקות (full/smoke/regression/security)
- `FORCE_DEPLOYMENT` - אילוץ deployment גם אם validation נכשל
Pipeline כולל timeout של 3 שעות ושומר 30 builds אחרונים.

**שאלה 2:** מה השלבים העיקריים ב-Jenkins pipeline ואיך הוא מתקשר עם Test Host?

**תשובה:** Pipeline כולל 4 שלבים עיקריים:
1. **Validation & Setup** - בדיקת פרמטרים ו-NFS mount availability
2. **Pre-Flight Checks** - בדיקת זמינות Test Host ו-framework באמצעות SSH
3. **Hardware Validation Execution** - הרצת הבדיקות על Test Host דרך `run_hw_tests.sh`
4. **Results Collection** - איסוף תוצאות, logs ו-screenshots חזרה ל-Jenkins
התקשורת עם Test Host נעשית באמצעות SSH עם credentials מוגדרים (`jenkins-test-host-key`) והרצת סקריפטים מרוחקים.

**שאלה 3:** איך מוגדרים triggers ב-Jenkins pipeline ומתי הוא מופעל?

**תשובה:** Pipeline מוגדר עם מספר triggers:
- `pollSCM('H/5 * * * *')` - בדיקה תקופתית כל 5 דקות לשינויים
- `upstream(threshold: 'SUCCESS', upstreamProjects: 'BSP-Build-Pipeline')` - הפעלה אוטומטית כשה-BSP build pipeline מסתיים בהצלחה
- הרצה ידנית על ידי משתמשים
- External webhook triggers מ-filesystem monitoring או Artifactory

**שאלה 4:** איך מוגדרות משתני הסביבה ב-pipeline ומה התפקיד שלהם?

**תשובה:** משתני הסביבה מוגדרים בסעיף `environment`:
- `TEST_HOST`, `TEST_HOST_USER` - credentials לחיבור ל-Test Host
- `SLACK_CHANNEL`, `EMAIL_RECIPIENTS` - endpoints להתראות
- `NFS_ROOT`, `NFS_MOUNT_POINT`, `NFS_SERVER` - הגדרות NFS artifact store
- `FRAMEWORK_PATH`, `SCRIPTS_PATH`, `MANIFESTS_PATH` - נתיבים על Test Host
- `ARTIFACT_RETENTION_DAYS`, `CHECKSUM_ALGORITHM` - הגדרות ניהול artifacts

**שאלה 5:** איך מתבצעת בדיקת Pre-Flight ומה היא כוללת?

**תשובה:** שלב Pre-Flight Checks כולל:
- בדיקת זמינות Test Host דרך SSH connection test עם timeout של 30 שניות
- אימות שה-framework זמין על Test Host (`test -d ${FRAMEWORK_PATH}`)
- בדיקה שסקריפט `run_hw_tests.sh` קיים וניתן להרצה
- בדיקת NFS mount availability עם `mountpoint -q`
כל בדיקה כושלת גורמת לעצירת ה-pipeline עם הודעת שגיאה ברורה.

**שאלה 6:** איך מתבצעת הרצת הבדיקות על Test Host מ-Jenkins?

**תשובה:** בשלב Hardware Validation Execution:
- Jenkins מתחבר ל-Test Host דרך SSH עם `sshagent` credentials
- מריץ את `run_hw_tests.sh` עם כל הפרמטרים הנדרשים
- הסקריפט מקבל manifest path, build ID, NFS build path, test scope ו-Jenkins build number
- ה-exit code נשמר למעקב אחר הצלחה/כישלון
- אם `FORCE_DEPLOYMENT=true`, כישלונים לא עוצרים את ה-pipeline

**שאלה 7:** איך מתבצע איסוף תוצאות מ-Test Host חזרה ל-Jenkins?

**תשובה:** בשלב Results Collection:
- Jenkins יוצר תיקיות `test-results`, `logs`, `screenshots`
- משתמש ב-`scp` להעתקת קבצים מ-Test Host:
  - Test reports מ-`${FRAMEWORK_PATH}/test-results/*`
  - Execution logs מ-`${FRAMEWORK_PATH}/logs/latest/*`
  - Screenshots מכישלונים מ-`${FRAMEWORK_PATH}/screenshots/*.png`
- כל הקבצים מארכבים כ-Jenkins artifacts
- אם קיים `junit.xml`, התוצאות מפורסמות כ-test results

**שאלה 8:** איך מוגדרות התראות והודעות ב-pipeline?

**תשובה:** התראות מוגדרות בסעיף `post`:
- **Success**: הודעת Slack ירוקה ו-email עם פרטי ההצלחה
- **Failure**: הודעת Slack אדומה ו-email עם פרטי הכישלון
- כל הודעה כוללת Build ID, test scope, duration ו-Jenkins URL
- Slack messages משתמשים ב-emojis (✅ להצלחה, ❌ לכישלון)
- Email notifications כוללים קישור ל-Jenkins build לפרטים נוספים

**שאלה 9:** איך Pipeline מטפל בשגיאות ו-error recovery?

**תשובה:** Pipeline כולל מספר מנגנוני error handling:
- Timeout של 3 שעות למניעת hanging builds
- `try-catch` blocks בשלבים קריטיים עם logging מפורט
- בדיקת exit codes מכל פקודת SSH
- `|| true` בפקודות scp למניעת כישלון אם קבצים לא קיימים
- `FORCE_DEPLOYMENT` parameter לעקיפת כישלוני validation
- Automatic cleanup של temporary files ו-connections

**שאלה 10:** איך Pipeline תומך בסוגי build שונים ו-deployment strategies?

**תשובה:** Pipeline מזהה ותומך בסוגי build שונים:
- זיהוי אוטומטי של build type מ-manifest filename (dev/hotfix/stable)
- התאמת test scope לפי build type
- תמיכה ב-NFS ו-Artifactory artifact sources
- Auto-generation של NFS build path אם לא סופק
- פרמטריזציה של test execution לפי build requirements
- Archive של pipeline parameters ל-traceability
- תמיכה בהרצות manual ו-automated עם אותו pipeline
