CREATE TABLE Users (
UserID INT AUTO_INCREMENT PRIMARY KEY,
Username VARCHAR(50) NOT NULL UNIQUE,
Email VARCHAR(100) NOT NULL UNIQUE, 
PasswordHash CHAR(60) NOT NULL,
Role ENUM('player','admin') DEFAULT 'player',
 CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP, 
Status ENUM('active', 'inactive','banned') DEFAULT 'active' 
); 

CREATE TABLE Categories (
CategoryID INT AUTO_INCREMENT PRIMARY KEY, 
Name VARCHAR(50) NOT NULL UNIQUE ); 

CREATE TABLE Questions (
QuestionID INT AUTO_INCREMENT PRIMARY KEY,
CategoryID INT NOT NULL,
Text TEXT NOT NULL,
OptionA VARCHAR(255) NOT NULL,
OptionB VARCHAR(255) NOT NULL,
OptionC VARCHAR(255) NOT NULL,
OptionD VARCHAR(255) NOT NULL,
CorrectOption CHAR(1) CHECK (CorrectOption IN ('A','B','C','D')),
 Difficulty ENUM('easy','medium','hard') DEFAULT 'medium',
Status ENUM('pending','approved','rejected') DEFAULT 'pending',
WriterID INT NOT NULL ,
FOREIGN KEY (WriterID) REFERENCES Users (UserID) ,
FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID) 
); 

CREATE TABLE Matches (
MatchID INT AUTO_INCREMENT PRIMARY KEY,
StartTime DATETIME NOT NULL,
EndTime DATETIME,
Status ENUM('active','completed') DEFAULT 'active',
 Player1ID INT NOT NULL,
Player2ID INT,
WinnerID INT,
FOREIGN KEY (Player1ID) REFERENCES Users(UserID),
 FOREIGN KEY (Player2ID) REFERENCES Users(UserID), 
FOREIGN KEY (WinnerID) REFERENCES Users(UserID) 
);

CREATE TABLE Rounds (
RoundID INT AUTO_INCREMENT PRIMARY KEY,
MatchID INT NOT NULL,
QuestionID INT NOT NULL,
SequenceNo INT NOT NULL,
PlayerID INT NOT NULL,
SelectedOption CHAR(1) CHECK (SelectedOption IN ('A','B','C','D')),
 ResponseTime DECIMAL(5,2),
FOREIGN KEY (MatchID) REFERENCES Matches(MatchID),
FOREIGN KEY (QuestionID) REFERENCES Questions(QuestionID),
FOREIGN KEY (PlayerID) REFERENCES Users(UserID) 
);

CREATE TABLE PlayerStats (
UserID INT PRIMARY KEY,
TotalGames INT DEFAULT 0,
Wins INT DEFAULT 0,
Losses INT DEFAULT 0,
WinRate DECIMAL(5,2) AS (CASE WHEN TotalGames>0 THEN Wins/TotalGames*100 ELSE 0 END) STORED,
AvgAccuracy DECIMAL(5,2) DEFAULT 0,
XP INT DEFAULT 0,	
Level INT DEFAULT 1,
FOREIGN KEY (UserID) REFERENCES Users(UserID) ); 

CREATE TABLE LeaderboardScores (
  ScoreID         INT AUTO_INCREMENT PRIMARY KEY,
  UserID          INT NOT NULL,
  Score           INT NOT NULL,
  LeaderboardRank INT,                                
  Period          ENUM('weekly','monthly','alltime') NOT NULL,
  PeriodStart     DATE NOT NULL,
  PeriodEnd       DATE NOT NULL,
  UpdatedAt       DATETIME DEFAULT CURRENT_TIMESTAMP 
                    ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY ux_user_period_start (UserID, Period, PeriodStart),
  FOREIGN KEY (UserID) REFERENCES Users(UserID)
);

 CREATE TABLE AdminRoles (
    AdminID INT PRIMARY KEY,
    CanApproveQuestions BOOLEAN DEFAULT TRUE,
    CanBanUsers BOOLEAN DEFAULT TRUE,
    CanViewAllStats BOOLEAN DEFAULT TRUE,
    CanManageLeaderboard BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (AdminID) REFERENCES Users(UserID)
);

CREATE TABLE Messages (
    MessageID      INT AUTO_INCREMENT PRIMARY KEY,
    SenderID       INT NOT NULL,
    ReceiverID     INT NOT NULL,
    ParentMsgID    INT       NULL,
    Content        TEXT      NOT NULL,
    CreatedAt      DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    EditedAt       DATETIME  NULL,
    IsDeleted      TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (SenderID)   REFERENCES Users(UserID),
    FOREIGN KEY (ReceiverID) REFERENCES Users(UserID),
    FOREIGN KEY (ParentMsgID) REFERENCES Messages(MessageID)
);


