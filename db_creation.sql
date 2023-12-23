CREATE TABLE Member(
    member_id BIGINT PRIMARY KEY,
    total_points INTEGER CHECK(total_points >= 0),
    generated_points INTEGER CHECK(generated_points >= 0),
    opt_in BOOLEAN);
    
CREATE TABLE Gamba(
	gamba_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    gamba_text VARCHAR(250),
    is_open BOOLEAN,
    outcome BOOLEAN);
    
CREATE TABLE Gamba_option(
	gamba_option_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    gamba_option_text VARCHAR(250),
    gamba_id INTEGER,
    option_number INTEGER,
    CONSTRAINT gamba_option_reference FOREIGN KEY(gamba_id) REFERENCES GAMBA(gamba_id));
    
CREATE TABLE Point_change(
	pc_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    pc_timestamp DATETIME,
    amount INTEGER,
    member_id BIGINT,
    CONSTRAINT pc_reference FOREIGN KEY(member_id) REFERENCES Member(member_id));
    
CREATE TABLE Coinflip(
	pc_id INTEGER PRIMARY KEY,
    outcome BOOLEAN,
    CONSTRAINT cf_reference FOREIGN KEY(pc_id) REFERENCES Point_change(pc_id));
    
CREATE TABLE Duel(
	pc_id INTEGER PRIMARY KEY,
    initiator BOOLEAN,
    outcome BOOLEAN,
    opponent_id BIGINT,
    CONSTRAINT duel_reference_pc FOREIGN KEY(pc_id) REFERENCES Point_change(pc_id),
    CONSTRAINT duel_reference_opponent FOREIGN KEY (opponent_id) REFERENCES Member(member_id));

CREATE TABLE Gift(
	pc_id INTEGER PRIMARY KEY,
    initiator BOOLEAN,
    outcome BOOLEAN,
    receiver_id BIGINT,
    CONSTRAINT gift_reference_pc FOREIGN KEY(pc_id) REFERENCES Point_change(pc_id),
    CONSTRAINT gift_reference_opp FOREIGN KEY(receiver_id) REFERENCES Member(member_id));
    
CREATE TABLE Bet_set(
	pc_id INTEGER PRIMARY KEY,
    gamba_option_id INTEGER,
    gamba_id INTEGER,
    CONSTRAINT bs_reference_pc FOREIGN KEY(pc_id) REFERENCES Point_change(pc_id),
    CONSTRAINT bs_reference_gamba_option FOREIGN KEY(gamba_option_id) REFERENCES Gamba_option(gamba_option_id),
    CONSTRAINT bs_reference_gamba FOREIGN KEY(gamba_id) REFERENCES Gamba(gamba_id));
    
CREATE TABLE Bet_payout(
	pc_id INTEGER PRIMARY KEY,
    outcome BOOLEAN,
    bet_set_id INTEGER,
    CONSTRAINT bp_reference_pc FOREIGN KEY(pc_id) REFERENCES Point_change(pc_id),
    CONSTRAINT bp_reference_bet_set_id FOREIGN KEY(bet_set_id) REFERENCES Bet_set(pc_id));

CREATE TRIGGER pc_updater AFTER INSERT ON Point_change FOR EACH ROW
	UPDATE Member SET total_points = total_points + NEW.amount WHERE Member.member_id = NEW.member_id;
    
CREATE TRIGGER generator_updater BEFORE UPDATE ON Member FOR EACH ROW
	SET NEW.total_points = NEW.total_points + NEW.generated_points - OLD.generated_points;