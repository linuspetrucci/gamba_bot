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

    def opt_in(self, member_id: int):
        sql = '''UPDATE Member SET opt_in = 1 WHERE member_id = %s'''
        values = (member_id,)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()

    def update_generator(self, member_id: int, amount: int):
        query = '''SELECT generated_points FROM Member WHERE member_id = %s'''
        cursor = self.connection.cursor()
        cursor.execute(query)
        row = cursor.fetchall()
        generated_points = row[0][0]
        sql = '''UPDATE Member SET generated_points = %s WHERE member_id = %s'''
        cursor.execute(sql, (generated_points + amount, member_id))
        self.connection.commit()

    def add_gamba(self, text: str):
        sql = '''INSERT INTO Gamba (gamba_text, is_open, outcome) VALUES (%s, TRUE, NULL)'''
        values = (text,)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()
        return cursor.lastrowid

    def add_gamba_option(self, text: str, gamba_id: int, option_number: int):
        sql = '''INSERT INTO Gamba_option(gamba_option_text, gamba_id, option_number) VALUES (%s, %s, %s)'''
        values = (text, gamba_id, option_number)
        cursor = self.connection.cursor()
        cursor.execute(sql, values)
        self.connection.commit()

    def add_coinflip(self, member_id: int, amount: int, outcome: bool):
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (amount, member_id)
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
        query = '''SELECT gamba_option_id FROM Gamba_option WHERE Gamba_option.gamba_id = %s AND 
        Gamba_option.option_number = %s'''
        values = (gamba_id, option_number)
        cursor.execute(query, values)
        gamba_option_id = cursor.fetchone()[0]
        sql = '''INSERT INTO Bet_set(pc_id, gamba_option_id, gamba_id) VALUES (%s, %s, %s)'''
        values = (cursor.lastrowid, gamba_option_id, gamba_id)
        cursor.execute(sql, values)
        self.connection.commit()

    def payout_bet(self, member_id: int, outcome: bool, gamba_id: int):
        query = '''SELECT Bet_set.pc_id, Point_change.amount FROM (Bet_set INNER JOIN Point_change ON Bet_set.pc_id = Point_change.pc_id)
        WHERE member_id = %s AND gamba_id = %s'''
        values = (member_id, gamba_id)
        cursor = self.connection.cursor()
        cursor.execute(query, values)
        rows = cursor.fetchall()
        bet_set_id = rows[0][0]
        amount = rows[0][1]
        sql = '''INSERT INTO Point_change(pc_timestamp, amount, member_id) VALUES (NOW(), %s, %s)'''
        values = (amount, member_id)
        cursor.execute(sql, values)
        sql = '''INSERT INTO Bet_payout(pc_id, outcome, bet_set_id) VALUES (%s)'''
        values = (cursor.lastrowid, outcome, bet_set_id)
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
