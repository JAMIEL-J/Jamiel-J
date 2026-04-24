![Header](https://capsule-render.vercel.app/api?type=waving&color=0D1117,1a1a2e,16213e&height=200&section=header&text=Jamiel%20J&fontSize=60&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Data%20Analyst%20%7C%20SQL%20%C2%B7%20Python%20%C2%B7%20Power%20BI%20%7C%20Building%20with%20AI&descSize=18&descAlignY=58&descColor=8b9dc3)

<div align="center">

![Typing](https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=18&pause=1800&color=8B9DC3&center=true&vCenter=true&width=560&lines=Building+production-ready+data+and+AI+systems;Analytics+that+ship+with+business+impact)

![Divider](https://img.shields.io/badge/%E2%9C%A6%20Data%20%7C%20AI%20%7C%20Automation%20%E2%9C%A6-0D1117?style=flat-square&labelColor=0D1117&color=1A1A2E)

</div>

<div align="center">

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/jamiel-j-856ab9329/)
[![Portfolio](https://img.shields.io/badge/Portfolio-00C7B7?style=flat-square&logo=netlify&logoColor=white)](https://jamiel-j.netlify.app/)
[![Email](https://img.shields.io/badge/Email-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:jahirjamiel@gmail.com)
![Open to Work](https://img.shields.io/badge/Open%20to%20Work-1D9E75?style=flat-square&logo=checkmarx&logoColor=white)
![Profile Views](https://komarev.com/ghpvc/?username=JAMIEL-J&style=flat-square&color=1D9E75&label=Profile+Views)

</div>

---

**Data Analyst** — I turn messy datasets into decisions that actually move numbers.

Final-year B.Tech IT student at MIET, Tiruchirappalli (graduating June 2026). I spent the last two years building things that work in production, not just in notebooks — an NL-to-SQL analytics platform, an offline voice assistant, and a set of analytics projects that quantify their own results. I'm actively looking for Data Analyst / ML Analyst roles, open to remote and full-time.

- 📍 Pudukkottai, India — open to remote & relocation
- 💼 Interned at BY8LABS AI — KPI dashboards, EDA, data validation pipelines
- 🔨 Currently building: JD-Match (multi-agent job intelligence system, LangGraph)
- 📬 Reach me: jahirjamiel@gmail.com · +91 78453 01134

---

## Tech stack

<div align="center">

<img src="https://skillicons.dev/icons?i=python,mysql,git,github,vscode,jupyter,fastapi,react&theme=dark" />

<br/><br/>

![Power BI](https://img.shields.io/badge/Power_BI-F2C811?style=flat-square&logo=microsoftpowerbi&logoColor=black)
![Tableau](https://img.shields.io/badge/Tableau-E97627?style=flat-square&logo=tableau&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=flat-square&logo=duckdb&logoColor=black)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-669DF6?style=flat-square&logo=googlecloud&logoColor=white)
![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?style=flat-square&logo=snowflake&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=amazonwebservices&logoColor=white)

</div>

I don't list frameworks I haven't shipped something with.

---

## Projects

### [Vizzy Analytics](https://github.com/JAMIEL-J/Vizzy-Analytics)

NL-to-SQL analytics platform. Ask a question in plain English — get a validated SQL query, a chart, and a business narrative, automatically. Built SQLGlot validation to catch hallucinated SQL before it touches the database. Hits **104ms p95** query time on **1M rows** via DuckDB. Has JWT + RBAC, append-only audit logs, and a governed cleaning workflow so nothing happens to your data without approval.

`FastAPI` `DuckDB` `React 19` `Groq (Llama 3.3-70b)` `SQLGlot` `JWT/RBAC` `SQLModel` `Recharts` `Zustand`

<br/>

[![Vizzy](https://github-readme-stats.vercel.app/api/pin/?username=JAMIEL-J&repo=Vizzy-Analytics&theme=tokyonight&hide_border=true)](https://github.com/JAMIEL-J/Vizzy-Analytics)

---

### [DNA Voice Assistant](https://github.com/JAMIEL-J/DNA-Desktop-Assistant-)

Offline-capable voice assistant for Windows 11. Runs faster-whisper (base, int8, VAD filter) for STT, Piper TTS for speech, OpenWakeWord for always-on detection, and Gemma 4 31B via Gemini API for reasoning. Uses a regex-first intent router so simple commands never touch the LLM — keeps latency low on 8GB RAM with no GPU. 3-state session model with mic gating after TTS to prevent echo loops.

`Python` `faster-whisper` `Piper TTS` `OpenWakeWord` `Gemma 4` `Gemini API` `SQLite` `DuckDB`

<br/>

[![DNA](https://opengraph.githubassets.com/1/JAMIEL-J/DNA-Desktop-Assistant-)](https://github.com/JAMIEL-J/DNA-Desktop-Assistant-)

---

### Analytics projects — results, not just code

| Project | What it found | Stack |
|:---|:---|:---|
| [**Fraud Detection**](https://github.com/JAMIEL-J/Customer-Lifetime-Intelligence) | 99.76% recall · ROC-AUC 0.9993 · threshold-optimized for minimum missed fraud | LightGBM · SMOTE · Scikit-learn |
| [**Demand Forecasting**](https://github.com/JAMIEL-J/Demand-Forecasting-and-Inventory-Optimization) | 4.01% WAPE across 45 stores · 31.7% over baseline · outputs fed into inventory policy | Prophet · SARIMAX · Quantile Regression |
| [**Revenue Leak / Funnel**](https://github.com/JAMIEL-J/Conversion-Funnel-Analysis) | $1.14M annual leakage identified in cart abandonment + checkout drop-off | Python · Pandas · EDA |
| [**RFM Segmentation**](https://github.com/JAMIEL-J/Sales-performance-Optimization) | Top 20% customers = 65% revenue · territory inefficiency mapping | Python · RFM · Pandas |
| [**Hospital Analytics**](https://github.com/JAMIEL-J/Hospital-Analytics) | Patient flow + resource utilization dashboard for operational decisions | Python · BI |
| [**House Rent Predictor**](https://github.com/JAMIEL-J/House-Rent-Predictor) | ML regression model deployed as a live Streamlit web app | Python · Streamlit · Scikit-learn |

---

## GitHub activity

<div align="center">

<img src="https://github-readme-stats.vercel.app/api?username=JAMIEL-J&show_icons=true&theme=tokyonight&hide_border=true&include_all_commits=true&count_private=true&hide=prs" height="160"/>
<img src="https://github-readme-stats.vercel.app/api/top-langs/?username=JAMIEL-J&layout=compact&theme=tokyonight&hide_border=true&langs_count=6&hide=jupyter%20notebook,html" height="160"/>

</div>

<div align="center">

[![Streak](https://streak-stats.demolab.com?user=JAMIEL-J&theme=tokyonight&hide_border=true&date_format=M%20j%5B%2C%20Y%5D)](https://github.com/JAMIEL-J)

</div>

<div align="center">

[![Activity Graph](https://github-readme-activity-graph.vercel.app/graph?username=JAMIEL-J&theme=tokyo-night&hide_border=true&area=true&custom_title=Contribution%20Activity)](https://github.com/JAMIEL-J)

</div>

---

## Currently building

**JD-Match** — Multi-agent job intelligence system using LangGraph. Parses job descriptions, extracts structured requirements, and matches them against candidate profiles with scored output. Solves the problem of applying blind without knowing what a JD actually weights.

Also wrapping up final documentation and submission for Vizzy as my B.Tech final-year project (June 2026).

---

## Let's talk

If you're hiring for a Data Analyst, ML Analyst, or Data Scientist role — remote or full-time — I'm actively looking.

📧 jahirjamiel@gmail.com  
📞 +91 78453 01134  
🔗 [LinkedIn](https://www.linkedin.com/in/jamiel-j-856ab9329/)  
🌐 [Portfolio](https://jamiel-j.netlify.app/)

<div align="center">

[![Connect on LinkedIn](https://img.shields.io/badge/Connect%20on%20LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/jamiel-j-856ab9329/)

</div>

---

*I read my own project READMEs like a skeptic. If something looks thin, I fix it before listing it here.*

![Footer](https://capsule-render.vercel.app/api?type=waving&color=0D1117,1a1a2e,16213e&height=100&section=footer)
