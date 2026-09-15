from werkzeug.security import generate_password_hash
from app.database import get_db
def seed_demo_data():
    db=get_db()
    db.execute("DELETE FROM users WHERE username = ?", ("student",))
    for u,p,r in [("admin","admin","admin"),("teacher","teacher","teacher")]:
        db.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",(u,generate_password_hash(p),r))
    for x in ["П-21","П-22","П-23","ИС-21"]: db.execute("INSERT OR IGNORE INTO groups_ref(name) VALUES(?)",(x,))
    ts=[("Иванов Сергей Владимирович","ИВ","#4f46e5"),("Петрова Анна Игоревна","ПА","#16a34a"),("Сидоров Дмитрий Андреевич","СД","#ca8a04")]
    for x in ts: db.execute("INSERT INTO teachers(full_name,short_name,color) SELECT ?,?,? WHERE NOT EXISTS(SELECT 1 FROM teachers WHERE full_name=?)",(*x,x[0]))
    for x in [("Информатика","#2563eb"),("Программирование","#7c3aed"),("Математика","#dc2626"),("Физика","#ea580c"),("Базы данных","#0891b2")]:
        db.execute("INSERT OR IGNORE INTO subjects(name,color) VALUES(?,?)",x)
    for x in ["204","305","312","401"]: db.execute("INSERT OR IGNORE INTO classrooms(name) VALUES(?)",(x,))
    if db.execute("SELECT COUNT(*) c FROM lessons").fetchone()["c"]==0:
        g=db.execute("SELECT id FROM groups_ref").fetchall(); t=db.execute("SELECT id FROM teachers").fetchall(); s=db.execute("SELECT id FROM subjects").fetchall(); c=db.execute("SELECT id FROM classrooms").fetchall()
        for i in range(4):
            db.execute("INSERT INTO lessons(group_id,teacher_id,subject_id,classroom_id,weekday,period,week,lesson_type,note) VALUES(?,?,?,?,?,?,?,?,?)",(g[i]["id"],t[i%3]["id"],s[i%5]["id"],c[i%4]["id"],i + 1,1,1,"Лекция","Демо"))
    db.commit()
