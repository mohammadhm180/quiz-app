from datetime import time, datetime, timedelta

import mysql.connector
import bcrypt
import getpass
import random
import sys

DB_CONF = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Avengers',
    'database': 'QK'
}


class QuizApp:
    def __init__(self):
        self.conn = mysql.connector.connect(**DB_CONF)
        self.cursor = self.conn.cursor(dictionary=True)
        self.user = None

    # ========= AUTH =========
    def register(self):
        print("\n=== Register ===")
        uname = input("Username: ").strip()
        email = input("Email: ").strip()
        pwd = getpass.getpass("Password: ")
        try:
            pw_hash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
            self.cursor.execute(
                "INSERT INTO Users (Username, Email, PasswordHash) VALUES (%s, %s, %s)",
                (uname, email, pw_hash.decode())
            )
            self.conn.commit()
            print("✅ Registered successfully!\n")
        except mysql.connector.errors.IntegrityError:
            print("❌ Username or Email already exists.\n")

    def login(self):
        print("\n=== Login ===")
        email = input("Email: ").strip()
        pwd = getpass.getpass("Password: ")
        self.cursor.execute("SELECT * FROM Users WHERE Email=%s", (email,))
        row = self.cursor.fetchone()
        if row and bcrypt.checkpw(pwd.encode(), row['PasswordHash'].encode()):
            if row["Status"] == "banned":
                print("❌ you are banned.\n")
            elif row["Status"] == "inactive":
                print("❌ your account is inactive.\n")
            else:
                self.user = row
                print(f"✅ Welcome, {row['Username']} ({row['Role']})\n")
        else:
            print("❌ Invalid credentials.\n")

    def logout(self):
        if self.user:
            print(f"Goodbye, {self.user['Username']}!\n")
            self.user = None
        else:
            print("You are not logged in.\n")

    # ========= ROLE UTILS =========
    def is_admin(self):
        return self.user and self.user['Role'] == 'admin'

    def load_admin_roles(self):
        if not self.is_admin():
            return None
        self.cursor.execute("SELECT * FROM AdminRoles WHERE AdminID=%s", (self.user['UserID'],))
        return self.cursor.fetchone()

    # ========= GAME =========
    def play(self):
        if not self.user:
            return print("❌ Please login first.\n")

        print("\n=== New Match ===")
        opponent = input("Opponent username (or leave blank for random): ").strip()

        if opponent:
            self.cursor.execute("SELECT UserID FROM Users WHERE Username=%s and Status='active'", (opponent,))
            opp = self.cursor.fetchone()
            pid2 = opp['UserID'] if opp else None
            if not pid2:
                print("❌ Opponent not found.\n")
                return
        else:
            self.cursor.execute("SELECT UserID FROM Users WHERE UserID<>%s and Status='active' ORDER BY RAND() LIMIT 1",
                                (self.user['UserID'],))
            res = self.cursor.fetchone()
            if not res:
                print("❌ No available opponents.\n")
                return
            pid2 = res['UserID']

        self.cursor.execute("INSERT INTO Matches (StartTime, Player1ID, Player2ID) VALUES (NOW(), %s, %s)",
                            (self.user['UserID'], pid2))
        mid = self.cursor.lastrowid
        self.conn.commit()

        self.cursor.execute("""
                    SELECT count(*) as count
                    FROM Questions
                    WHERE Status = 'approved'
                """)
        qr=self.cursor.fetchone();
        if qr['count']<5:
            print("❌ currently there is not enough question for match.\n")
            return

        correct_answers=0
        old_question_ids = set()

        for seq in range(1, 4):
            if old_question_ids:
                placeholders = ', '.join(['%s'] * len(old_question_ids))
                sql = f"""
                    SELECT QuestionID, Text, OptionA, OptionB, OptionC, OptionD,CorrectOption
                    FROM Questions
                    WHERE Status = 'approved' AND QuestionID NOT IN ({placeholders})
                    ORDER BY RAND()
                    LIMIT 1
                """
                self.cursor.execute(sql, tuple(old_question_ids))
            else:
                self.cursor.execute("""
                    SELECT QuestionID, Text, OptionA, OptionB, OptionC, OptionD,CorrectOption
                    FROM Questions
                    WHERE Status = 'approved'
                    ORDER BY RAND()
                    LIMIT 1
                """)

            q = self.cursor.fetchone()
            if not q:
                print("❌ No approved questions found.\n")
                return

            question_id = q['QuestionID']
            old_question_ids.add(question_id)
            print(f"\nQ{seq}: {q['Text']}")
            for o in ['A', 'B', 'C', 'D']:
                print(f" {o}) {q['Option' + o]}")

            start_time = datetime.now()

            while 1 == 1:
                ans = input("Your answer: ").strip().upper()
                if ans not in ['A', 'B', 'C', 'D']:
                    print("❌ Invalid option. Try Again")
                else:
                    break
            if ans==q['CorrectOption']:
                correct_answers=correct_answers+1
                print("Yes you are right!")
            else:
                print("Oh that is the wrong answer.")
            response_time = (datetime.now() - start_time).total_seconds()
            round(response_time,2)

            self.cursor.execute("""
                INSERT INTO Rounds (MatchID, QuestionID, SequenceNo, PlayerID, SelectedOption, ResponseTime)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (mid, q['QuestionID'], seq, self.user['UserID'], ans, response_time))
            self.conn.commit()
        winnerId = self.user['UserID']
        if correct_answers!=3:
            print("You Lost❌")
            winnerId=pid2
        else:
            print("You Won!")

        self.cursor.execute("UPDATE Matches SET EndTime=NOW(), Status='completed', WinnerID=%s WHERE MatchID=%s", (winnerId,mid))
        self.conn.commit()
        print("\n✅ Match complete!\n")

    # ========= PLAYER =========
    def stats(self):
        if not self.user:
            return print("❌ Please login first.\n")

        self.cursor.execute("SELECT * FROM PlayerStats WHERE UserID=%s", (self.user['UserID'],))
        ps = self.cursor.fetchone()
        print("\n=== Your Player Stats ===")
        for k, v in ps.items():
            print(f"{k}: {v}")

        print("\n=== Your Leaderboard Scores ===")
        self.cursor.execute("""
            SELECT Period, PeriodStart, PeriodEnd, Score, LeaderboardRank
            FROM LeaderboardScores
            WHERE UserID = %s
            ORDER BY FIELD(Period, 'weekly', 'monthly', 'alltime'), PeriodStart DESC
        """, (self.user['UserID'],))

        lb = self.cursor.fetchall()
        for row in lb:
            print(f"{row['Period'].capitalize()} ({row['PeriodStart']} → {row['PeriodEnd']}): {row['Score']} pts")

    def match_history(self):
        if not self.user:
            return print("❌ Please login first.\n")

        self.cursor.execute("""
            SELECT M.MatchID, M.StartTime, M.EndTime, 
                   CASE 
                       WHEN M.Player1ID = %s THEN U2.Username
                       ELSE U1.Username 
                   END AS Opponent,
                   CASE 
                       WHEN M.WinnerID = %s THEN 'Win' 
                       ELSE 'Loss' 
                   END AS Result
            FROM Matches M
            JOIN Users U1 ON U1.UserID = M.Player1ID
            JOIN Users U2 ON U2.UserID = M.Player2ID
            WHERE (M.Player1ID = %s OR M.Player2ID = %s)
              AND M.Status = 'completed'
            ORDER BY M.StartTime DESC
        """, (self.user['UserID'], self.user['UserID'], self.user['UserID'], self.user['UserID']))

        matches = self.cursor.fetchall()
        print("\n=== Match History ===")
        for m in matches:
            print(
                f"Match {m['MatchID']} | {m['StartTime']} → {m['EndTime']} | vs {m['Opponent']} | Result: {m['Result']}")
        print()

    def top_players_by_winrate(self):
        self.cursor.execute("""
            SELECT U.Username, PS.WinRate
            FROM PlayerStats PS
            JOIN Users U ON U.UserID = PS.UserID
            WHERE PS.TotalGames >= 5
            ORDER BY PS.WinRate DESC
            LIMIT 10
        """)
        rows = self.cursor.fetchall()
        print("\n=== Top 10 Players by Win Rate ===")
        for i, r in enumerate(rows, start=1):
            print(f"{i}. {r['Username']} - {r['WinRate']}%")
        print()

    def most_played_categories(self):
        self.cursor.execute("""
            SELECT C.Name AS Category, COUNT(*) AS Total
            FROM Rounds R
            JOIN Questions Q ON R.QuestionID = Q.QuestionID
            JOIN Categories C ON Q.CategoryID = C.CategoryID
            GROUP BY C.Name
            ORDER BY Total DESC
            LIMIT 5
        """)
        rows = self.cursor.fetchall()
        print("\n=== Most Played Categories ===")
        for r in rows:
            print(f"{r['Category']}: {r['Total']} rounds played")
        print()

    def leaderboard(self):
        if not self.user:
            print("❌ Please login first.\n")
            return

        print("\n=== Choose Leaderboard Period ===")
        print("1. Weekly")
        print("2. Monthly")
        print("3. All-Time")
        choice = input("Select period (1/2/3): ").strip()

        period_map = {
            '1': 'weekly',
            '2': 'monthly',
            '3': 'alltime'
        }

        period = period_map.get(choice)
        if not period:
            print("❌ Invalid choice.\n")
            return

        # Get current period boundaries
        today = datetime.now().date()
        if period == 'weekly':
            start_date = today - timedelta(days=today.weekday())
        elif period == 'monthly':
            start_date = today.replace(day=1)
        else:  # alltime
            start_date = datetime(1970, 1, 1).date()

        self.cursor.execute("""
            SELECT 
                U.Username, L.UserID, L.Score,
                RANK() OVER (ORDER BY L.Score DESC) AS LeaderboardRank
            FROM LeaderboardScores L
            JOIN Users U ON L.UserID = U.UserID
            WHERE L.Period = %s AND L.PeriodStart = %s
            ORDER BY L.Score DESC
            LIMIT 10
        """, (period, start_date))

        rows = self.cursor.fetchall()
        print(f"\n=== {period.capitalize()} Leaderboard ===")
        for i, row in enumerate(rows, 1):
            print(f"{i}. {row['Username']} - {row['Score']} pts")

        # Show user's own rank if not in top 10
        self.cursor.execute("""
            SELECT 
                RANK() OVER (ORDER BY Score DESC) AS MyRank, Score
            FROM LeaderboardScores
            WHERE Period = %s AND PeriodStart = %s
        """, (period, start_date))

        ranks = self.cursor.fetchall()
        for r in ranks:
            if r['MyRank'] > 10 and self.user['UserID'] == r.get('UserID'):
                print(f"\nYour Rank: {r['MyRank']} - {r['Score']} pts")
                break

    # ========= ADMIN =========
    def admin_menu(self):
        if not self.is_admin():
            return print("❌ You are not an admin.\n")

        roles = self.load_admin_roles()
        if not roles:
            return print("❌ No admin permissions set.\n")

        while True:
            print("\n=== Admin Menu ===")
            if roles['CanApproveQuestions']:
                print("1. Review Questions")
            if roles['CanBanUsers']:
                print("2. Ban User")
                print("3. Activate User")
            print("0. Back")

            choice = input("Choose: ").strip()
            if choice == '1' and roles['CanApproveQuestions']:
                self.review_questions()
            elif choice == '2' and roles['CanBanUsers']:
                self.ban_user()
            elif choice == '3' and roles['CanBanUsers']:
                self.active_user()
            elif choice == '0':
                break
            else:
                print("❌ Invalid or unauthorized.")

    def review_questions(self):
        self.cursor.execute("SELECT * FROM Questions WHERE Status='pending' LIMIT 1")
        q = self.cursor.fetchone()
        if not q:
            print("No pending questions.\n")
            return
        print(f"\nQuestion: {q['Text']}")
        print(f"A) {q['OptionA']}")
        print(f"B) {q['OptionB']}")
        print(f"C) {q['OptionC']}")
        print(f"D) {q['OptionD']}")
        print(f"Correct Option: {q['CorrectOption']}")

        decision = input("Approve (A) / Reject (R): ").strip().upper()
        if decision == 'A':
            self.cursor.execute("UPDATE Questions SET Status='approved' WHERE QuestionID=%s", (q['QuestionID'],))
            print("✅ Approved.\n")
        elif decision == 'R':
            self.cursor.execute("UPDATE Questions SET Status='rejected' WHERE QuestionID=%s", (q['QuestionID'],))
            print("❌ Rejected.\n")
        else:
            print("❌ Invalid choice.")
            return
        self.conn.commit()

    def ban_user(self):
        uname = input("Enter username to ban: ").strip()
        self.cursor.execute("UPDATE Users SET Status='banned' WHERE Username=%s", (uname,))
        if self.cursor.rowcount > 0:
            print(f"✅ User '{uname}' banned.\n")
            self.conn.commit()
        else:
            print("❌ User not found.\n")

    def active_user(self):
        uname = input("Enter username to activate: ").strip()
        self.cursor.execute("UPDATE Users SET Status='active' WHERE Username=%s", (uname,))
        if self.cursor.rowcount > 0:
            print(f"✅ User '{uname}' activated.\n")
            self.conn.commit()
        else:
            print("❌ User not found.\n")


    def send_message(self):
        """Send a message (or reply) to another user."""
        if not self.user:
            print("❌ Please login first.\n")
            return

        to_username = input("To (username): ").strip()
        content     = input("Message: ").strip()

        # find recipient
        self.cursor.execute(
            "SELECT UserID FROM Users WHERE Username = %s AND Status = 'active'",
            (to_username,)
        )
        row = self.cursor.fetchone()
        if not row:
            print("❌ Recipient not found or not active.\n")
            return
        rid = row['UserID']

        # insert
        self.cursor.execute(
            "INSERT INTO Messages (SenderID, ReceiverID, Content) VALUES (%s, %s, %s)",
            (self.user['UserID'], rid, content)
        )
        self.conn.commit()
        print("✅ Message sent.\n")

    def receive_messages(self):
        """View your inbox, optionally filtering by sender."""
        if not self.user:
            print("❌ Please login first.\n")
            return

        sender = input("From (leave blank for all): ").strip() or None
        params = [self.user['UserID']]
        sql = """
            SELECT M.MessageID, U1.Username AS Sender, M.Content, M.CreatedAt
            FROM Messages M
            JOIN Users U1 ON M.SenderID = U1.UserID
            WHERE M.ReceiverID = %s AND M.IsDeleted = 0
        """
        if sender:
            sql += " AND U1.Username = %s"
            params.append(sender)

        sql += " ORDER BY M.CreatedAt DESC"
        self.cursor.execute(sql, tuple(params))
        msgs = self.cursor.fetchall()

        if not msgs:
            print("\n📭 No messages found.\n")
            return

        print("\n=== Inbox ===")
        for idx, m in enumerate(msgs, start=1):
            ts = m['CreatedAt'].strftime("%Y-%m-%d %H:%M")
            print(f"{idx}. From {m['Sender']} @ {ts}")
            print(f"   » {m['Content']}\n")

    def _list_sent_messages(self):
        """Helper: fetch and return your last 10 sent, undeleted messages."""
        self.cursor.execute(
            """
            SELECT MessageID, U2.Username AS Receiver, Content, M.CreatedAt
            FROM Messages M
            JOIN Users U2 ON M.ReceiverID = U2.UserID
            WHERE M.SenderID = %s AND M.IsDeleted = 0
            ORDER BY M.CreatedAt DESC
            LIMIT 10
            """,
            (self.user['UserID'],)
        )
        return self.cursor.fetchall()

    def edit_message(self):
        """Show your recent sent messages, pick one to edit."""
        if not self.user:
            print("❌ Please login first.\n")
            return

        msgs = self._list_sent_messages()
        if not msgs:
            print("❌ You have no messages to edit.\n")
            return

        print("\nSelect a message to edit:")
        for i, m in enumerate(msgs, start=1):
            ts = m['CreatedAt'].strftime("%Y-%m-%d %H:%M")
            print(f"{i}. To {m['Receiver']} @ {ts}: {m['Content'][:30]}…")
        choice = int(input("Enter number: ").strip())
        msg = msgs[choice-1]

        new_text = input("New content: ").strip()
        self.cursor.execute(
            "UPDATE Messages SET Content=%s, EditedAt=NOW() WHERE MessageID=%s",
            (new_text, msg['MessageID'])
        )
        self.conn.commit()
        print("✅ Message updated.\n")

    def delete_message(self):
        """Show your recent sent messages, pick one to delete (soft)."""
        if not self.user:
            print("❌ Please login first.\n")
            return

        msgs = self._list_sent_messages()
        if not msgs:
            print("❌ You have no messages to delete.\n")
            return

        print("\nSelect a message to delete:")
        for i, m in enumerate(msgs, start=1):
            ts = m['CreatedAt'].strftime("%Y-%m-%d %H:%M")
            print(f"{i}. To {m['Receiver']} @ {ts}: {m['Content'][:30]}…")
        choice = int(input("Enter number: ").strip())
        msg = msgs[choice-1]

        self.cursor.execute(
            "UPDATE Messages SET IsDeleted=1 WHERE MessageID=%s",
            (msg['MessageID'],)
        )
        self.conn.commit()
        print("✅ Message deleted.\n")

    def reply_message(self):
        """Show your inbox, pick one to reply to."""
        if not self.user:
            print("❌ Please login first.\n")
            return

        # reuse receive logic but return list
        self.cursor.execute(
            """
            SELECT M.MessageID, U1.Username AS Sender, Content, M.CreatedAt
            FROM Messages M
            JOIN Users U1 ON M.SenderID = U1.UserID
            WHERE M.ReceiverID = %s AND M.IsDeleted = 0
            ORDER BY M.CreatedAt DESC
            LIMIT 10
            """,
            (self.user['UserID'],)
        )
        msgs = self.cursor.fetchall()
        if not msgs:
            print("❌ No messages to reply to.\n")
            return

        print("\nSelect a message to reply:")
        for i, m in enumerate(msgs, start=1):
            ts = m['CreatedAt'].strftime("%Y-%m-%d %H:%M")
            print(f"{i}. From {m['Sender']} @ {ts}: {m['Content'][:30]}…")
        choice = int(input("Enter number: ").strip())
        orig = msgs[choice-1]

        reply = input("Your reply: ").strip()

        # determine target: original sender
        self.cursor.execute(
            "SELECT UserID FROM Users WHERE Username=%s",
            (orig['Sender'],)
        )
        rid = self.cursor.fetchone()['UserID']

        self.cursor.execute(
            """
            INSERT INTO Messages (SenderID, ReceiverID, ParentMsgID, Content)
            VALUES (%s, %s, %s, %s)
            """,
            (self.user['UserID'], rid, orig['MessageID'], reply)
        )
        self.conn.commit()
        print("✅ Reply sent.\n")

def main_menu():
    app = QuizApp()
    options = {
        '1': ('Register', app.register),
        '2': ('Login', app.login),
        '3': ('Logout', app.logout),
        '4': ('Play Game', app.play),
        '5': ('View Stats', app.stats),
        '6': ('Leaderboard', app.leaderboard),
        '7': ('Admin Menu', app.admin_menu),
        '8': ('Match History', app.match_history),
        '9': ('Top Players by Win Rate', app.top_players_by_winrate),
        '10': ('Most Played Categories', app.most_played_categories),
        '11': ('Send Message',app.send_message),
        '12': ('View Inbox',app.receive_messages),
        '13': ('Edit Message',app.edit_message),
        '14': ('Delete Message', app.delete_message),
        '15': ('Reply to Message',app.reply_message),
        '0': ('Exit', lambda: sys.exit(0)),
    }

    while True:
        print("\n=== Main Menu ===")
        for key, (desc, _) in options.items():
            print(f"{key}. {desc}")
        choice = input("Choose an option: ").strip()
        action = options.get(choice)
        if action:
            try:
                action[1]()
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("❌ Invalid option.")


if __name__ == '__main__':
    main_menu()
