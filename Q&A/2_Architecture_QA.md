# Architecture - שאלות ותשובות

**שאלה 1:** מה המטרה הארכיטקטונית העליונה של הפרויקט ואיך היא מתבטאת במבנה המערכת?

**תשובה:** הפרויקט מממש "glass box" validation framework עבור ZCU102 BSP. הארכיטקטורה מעוצבת לספק שקיפות מלאה מ-source commit → build artifacts → hardware test execution → metrics/logs. המבנה כולל:
- `test_host/` - Python automation framework
- `infra/` - Infrastructure-as-Code (ELK, Prometheus)
- `docs/` - מדריכי ארכיטקטורה ותפעול
- `Jenkinsfile` - CI/CD pipeline המתאם NFS/Artifactory עם Test Host

**שאלה 2:** איך Jenkins משתלב בארכיטקטורה הכללית ומה תפקידו של Test Host?

**תשובה:** Jenkins משמש כמתאם מרכזי בין builds למעבדת הבדיקות. הוא מופעל על ידי upstream BSP build jobs, מאתר BSP manifest ו-artifacts ב-NFS/Artifactory, ומריץ מרחוק את framework הולידציה על Test Host באמצעות SSH. Test Host הוא מכונת Linux שמריצה את framework ה-Python/pytest, שולטת בחומרת המעבדה (power controllers, JTAG, serial, network), גושת NFS או גושת Artifactory לקבלת BSP artifacts, ושולחת logs ו-metrics ל-ELK ו-Prometheus/Grafana.

**שאלה 3:** איך מיוצגת החומרה בארכיטקטורה ומה העקרונות המנחים?

**תשובה:** משאבי החומרה מיוצגים דרך controllers ו-fixtures:
- Power: מוגדר ב-`config.yaml` תחת `hardware.power`, מופשט על ידי `create_power_controller`
- JTAG: מוגדר תחת `hardware.jtag` ומומש דרך `create_jtag_controller`
- Serial ו-network: מוגדרים תחת `hardware.serial` ו-`hardware.network`
הבדיקות משתמשות ב-validators ו-testers ברמה גבוהה (`BootValidator`, `UartTester`) במקום לדבר ישירות עם raw devices.

**שאלה 4:** איך הארכיטקטורה מטפלת בהבדלי קונפיגורציה וסביבה?

**תשובה:** הקונפיגורציה מוחצנת ל-YAML (`test_host/config.yaml`) ואפשרויות command-line. זה כולל serial ports, כתובות IP, הגדרות JTAG, הרכב test suite וקריטריוני קבלה. מעבדות או לוחות מרובים יכולים להיתמך על ידי מתן קבצי config שונים, תוך שמירה על אותו codebase.

**שאלה 5:** איפה observability מתאים לארכיטקטורה?

**תשובה:** Observability הוא דאגה מדרגה ראשונה:
- Metrics: נשלחים דרך Prometheus (Pushgateway) ומוצגים ב-Grafana
- Logs: מרוכזים ל-ELK (Elasticsearch, Logstash, Kibana) דרך `ELKReporter` ו-Filebeat/data shipper מה-Test Host
- Dashboards/alerts: מתוארים ב-`README.md` תחת *Observability and Metrics* ונתמכים על ידי הגדרות infra ב-`infra/`

**שאלה 6:** איך ה-framework משלב BSP manifests בארכיטקטורה?

**תשובה:** BSP manifests (למשל `bsp-main-137.yaml`) מתארים build metadata, רשימת artifacts, deployment config, runtime config ו-test plans. הארכיטקטורה מבטיחה ש:
- Jenkins מעביר את נתיב ה-manifest ל-Test Host
- ה-orchestrator מפרסר את ה-manifest ומגדיר artifacts ובדיקות באופן דינמי
זה קושר הרצת בדיקות ישירות ל-build המדויק שיצר את ה-firmware.

**שאלה 7:** איך יכולות בדיקה חדשות משתלבות ארכיטקטונית?

**תשובה:** ה-`docs/runbooks/Onboarding_New_Test_Case.md` מתאר את התהליך:
- הוספה או הרחבת test classes תחת `test_host/tests/` ומודולים תומכים ב-`framework/`
- עדכון `config.yaml` עם פרמטרי חומרה או בדיקה חדשים
- עדכון requirements אם נדרשות תלויות חדשות
- שילוב ה-suite החדש ב-Jenkins (למשל הוספת stages חדשים ב-pipeline)
זה שומר על הארכיטקטורה מודולרית וניתנת להרחבה.

**שאלה 8:** איך הארכיטקטורה תומכת בסקלביליות ולוחות עתידיים?

**תשובה:** פרטי לוח (כמו serial ports, התקני JTAG וקריטריוני קבלה) נמצאים בקונפיגורציה ו-manifests, בעוד שה-orchestration, controllers ו-reporters הם גנריים. על ידי פרמטריזציה של board type (למשל דרך `--board-type` ושדות manifest), אותה ארכיטקטורה יכולה לשמש מחדש עבור לוחות Zynq או Versal עתידיים עם שינויי קוד מינימליים.

**שאלה 9:** מה העקרונות המפתח שמנחים את הארכיטקטורה?

**תשובה:** הארכיטקטורה מונחית על ידי עקרונות מפתח:
- **Quality by Design**: כל commit מאומת אוטומטית מול חומרה אמיתית
- **Full Traceability**: כל artifact מגורסן וקשור ל-source commit שלו
- **Data-Driven Decisions**: metrics ו-logs עשירים מאפשרים החלטות release מושכלות
- **Developer Empowerment**: לולאות משוב מהירות ומידע debugging ברור
- **Automation First**: התערבות ידנית רק במקום שבו שיפוט אנושי מוסיף ערך

**שאלה 10:** איך הארכיטקטורה מבטיחה אמינות ו-resilience?

**תשובה:** הארכיטקטורה כוללת מנגנונים מרובים לאמינות:
- Hardware abstraction layers מאפשרים mock testing ללא תלות בחומרה פיזית
- Comprehensive logging ו-metrics מספקים visibility מלא לבעיות
- Power management מבטיח שלוחות נשארים במצב בטוח אחרי בדיקות
- Timeout mechanisms ו-error handling מונעים hanging processes
- Artifact validation עם checksums מבטיח תקינות deployment
- Multiple notification channels (Slack, email) מבטיחים שבעיות מדווחות במהירות
