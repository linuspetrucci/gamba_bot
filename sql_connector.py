import mysql.connector
import json

from mysql.connector import errorcode


class SQLConnector:
    def __init__(self):
        self.CONFIG = json.load(open('sql_credentials.json'))
        self.connection: mysql.connector.connection = self.get_connection()

    def add_member(self, member_id: int):
        sql = '''INSERT INTO Member (member_id, total_points, generated_points, opt_in) VALUES (%s, 0, 0, FALSE)'''
        values = (member_id,)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()

    def get_member_points(self, member_id: int) -> int:
        query = '''SELECT total_points FROM Member WHERE member_id = %s'''
        values = (member_id,)
        cursor = self.connection.cursor()
        cursor.execute(query, values)
        return cursor.fetchone()[0]

    def set_member_points(self, member_id: int, new_points: int):
        # TODO add SQL entity for set
        pass

    def get_all_member_ids(self) -> list[int]:
        query = '''SELECT member_id FROM Member'''
        cursor = self.connection.cursor()
        cursor.execute(query)
        return [member_id for (member_id,) in cursor.fetchall()]

    def opt_in(self, member_id: int):
        sql = '''UPDATE Member SET opt_in = TRUE WHERE member_id = %s'''
        values = (member_id,)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()

    def get_opt_in(self, member_id: int) -> bool:
        query = '''SELECT opt_in FROM Member WHERE member_id = %s'''
        values = (member_id,)
        cursor = self.connection.cursor()
        cursor.execute(query, values)
        return bool(cursor.fetchone()[0])

    def get_opt_in_members_sorted(self) -> list[(int, int, int)]:
        query = '''SELECT member_id, total_points, generated_points 
        FROM Member WHERE opt_in = TRUE ORDER BY total_points DESC'''
        cursor = self.connection.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def update_generator(self, member_id: int, amount: int):
        cursor = self.connection.cursor()
        sql = '''UPDATE Member SET generated_points = generated_points + %s WHERE member_id = %s'''
        values = (amount, member_id)
        cursor.execute(sql, values)
        self.connection.commit()

    def add_gamba(self, text: str) -> int:
        sql = '''INSERT INTO Gamba (gamba_text, is_open, outcome, gamba_message_id) VALUES (%s, TRUE, NULL, 0)'''
        values = (text,)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()
        return cursor.lastrowid

    def set_gamba_message_id(self, gamba_id: int, message_id: int):
        sql = '''UPDATE Gamba SET gamba_message_id = %s WHERE gamba_id = %s'''
        values = (message_id, gamba_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()

    def get_gamba_id_from_message_id(self, message_id: int) -> int:
        query = '''SELECT gamba_id FROM Gamba WHERE gamba_message_id = %s'''
        values = (message_id,)
        cursor = self.connection.cursor()
        cursor.execute(query, values)
        return cursor.fetchone()[0]

    def get_gamba_description_from_gamba_id(self, gamba_id: int) -> str:
        query = '''SELECT gamba_text FROM Gamba WHERE gamba_id = %s'''
        values = (gamba_id,)
        cursor = self.connection.cursor()
        cursor.execute(query, values)
        return cursor.fetchone()[0]

    def close_gamba(self, gamba_id: int, outcome: bool):
        sql = '''UPDATE Gamba SET outcome = %s, is_open = FALSE WHERE gamba_id = %s'''
        values = (outcome, gamba_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()

    def get_active_gamba_ids(self):
        query = '''SELECT gamba_id FROM Gamba WHERE is_open = TRUE'''
        cursor = self.connection.cursor()
        cursor.execute(query)
        return [gamba_id for (gamba_id,) in cursor.fetchall()]

    def add_gamba_option(self, text: str, gamba_id: int, option_number: int, payout_factor: float):
        sql = '''INSERT INTO Gamba_option(gamba_option_text, gamba_id, option_number, payout_factor) 
        VALUES (%s, %s, %s, %s)'''
        values = (text, gamba_id, option_number, payout_factor)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()

    def add_coinflip(self, member_id: int, amount: int, outcome: bool):
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (amount if outcome else -amount, member_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        sql = '''INSERT INTO Coinflip(pc_id, outcome) VALUES (%s, %s)'''
        values = (cursor.lastrowid, outcome)
        cursor.execute(sql, values)
        self.connection.commit()

    def add_duel(self, member_id: int, amount: int, outcome: bool, opponent_id: int, repeat: bool = True):
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (amount if outcome else -amount, member_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        sql = '''INSERT INTO Duel(pc_id, initiator, outcome, opponent_id) VALUES (%s, %s, %s, %s)'''
        values = (cursor.lastrowid, repeat, outcome, opponent_id)
        cursor.execute(sql, values)
        self.connection.commit()
        if repeat:
            self.add_duel(opponent_id, amount, not outcome, member_id, False)

    def add_gift(self, member_id: int, amount: int, receiver_id: int, repeat: bool = True):
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (-amount if repeat else amount, member_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        sql = '''INSERT INTO Gift(pc_id, initiator, receiver_id) VALUES (%s, %s, %s)'''
        values = (cursor.lastrowid, repeat, receiver_id)
        cursor.execute(sql, values)
        self.connection.commit()
        if repeat:
            self.add_gift(receiver_id, amount, member_id, False)

    def set_bet(self, member_id: int, amount: int, gamba_id: int, option_number: int):
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (-amount, member_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        pc_id = cursor.lastrowid
        query = '''SELECT gamba_option_id FROM Gamba_option WHERE Gamba_option.gamba_id = %s AND 
        Gamba_option.option_number = %s'''
        values = (gamba_id, option_number)
        cursor.execute(query, values)
        gamba_option_id_raw = cursor.fetchone()
        gamba_option_id = gamba_option_id_raw[0]
        sql = '''INSERT INTO Bet_set(pc_id, gamba_option_id, gamba_id) VALUES (%s, %s, %s)'''
        values = (pc_id, gamba_option_id, gamba_id)
        cursor.execute(sql, values)
        self.connection.commit()

    def get_bets_from_gamba_id(self, gamba_id: int) -> list[(int, int, int, int, float)]:
        query = '''SELECT Bet_set.pc_id, Point_change.amount, Point_change.member_id, Gamba_option.option_number,
         Gamba_option.payout_factor FROM ((Bet_set INNER JOIN Point_change ON Bet_set.pc_id = Point_change.pc_id) INNER
         JOIN Gamba_option ON Bet_set.gamba_option_id = Gamba_option.gamba_option_id) WHERE Bet_set.gamba_id = %s'''
        values = (gamba_id,)
        cursor = self.connection.cursor()
        cursor.execute(query, values)
        return cursor.fetchall()

    def payout_bet(self, member_id: int, outcome: bool, bet_set_id: int, amount: int):
        cursor = self.connection.cursor()
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (amount if outcome else 0, member_id)
        cursor.execute(sql, values)
        sql = '''INSERT INTO Bet_payout(pc_id, outcome, bet_set_id) VALUES (%s, %s, %s)'''
        values = (cursor.lastrowid, outcome, bet_set_id)
        cursor.execute(sql, values)
        self.connection.commit()

    def add_diceroll(self, member_id: int, amount: int, outcome: bool, rolled_value: int, predicted_numbers: str):
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (amount, member_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        sql = '''INSERT INTO Diceroll(pc_id, outcome, rolled_value, predicted_numbers) VALUES (%s, %s, %s, %s)'''
        values = (cursor.lastrowid, outcome, rolled_value, predicted_numbers)
        cursor.execute(sql, values)
        self.connection.commit()

    def add_set_points(self, member_id: int, target_amount: int):
        points_before = self.get_member_points(member_id)
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (target_amount - points_before, member_id)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        sql = '''INSERT INTO Set_points(pc_id, target_amount) VALUES (%s, %s)'''
        values = (cursor.lastrowid, target_amount)
        cursor.execute(sql, values)
        self.connection.commit()


    def get_connection(self):
        try:
            connection = mysql.connector.connect(**self.CONFIG)
        except mysql.connector.Error as error:
            if error.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            elif error.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(error)
        else:
            return connection
