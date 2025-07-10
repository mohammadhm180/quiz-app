DROP TRIGGER IF EXISTS trg_after_match_update;
DELIMITER $$

CREATE TRIGGER trg_after_match_update
AFTER UPDATE ON Matches
FOR EACH ROW
BEGIN
  DECLARE wkStart DATE;
  DECLARE wkEnd   DATE;
  DECLARE moStart DATE;
  DECLARE moEnd   DATE;
  DECLARE mDate   DATE;
  -- Only run if winner was just set
  IF NEW.WinnerID IS NOT NULL AND OLD.WinnerID IS NULL THEN
    -- Use match EndTime to determine bucket
    SET mDate = DATE(NEW.EndTime);
    SET wkStart = DATE_SUB(mDate, INTERVAL WEEKDAY(mDate) DAY);
    SET wkEnd   = DATE_ADD(wkStart, INTERVAL 6 DAY);
    SET moStart = DATE_FORMAT(mDate, '%Y-%m-01');
    SET moEnd   = LAST_DAY(mDate);
    -- Update winner stats
    UPDATE PlayerStats
    SET
      TotalGames  = TotalGames + 1,
      Wins        = Wins + 1,
      XP          = XP + 10,
      AvgAccuracy = CASE 
                      WHEN TotalGames + 1 > 0 
                        THEN (Wins + 1) / (TotalGames + 1) * 100 
                      ELSE 0 
                    END,
      Level       = FLOOR((XP + 10) / 100) + 1
    WHERE UserID = NEW.WinnerID;
    -- Update loser stats
    UPDATE PlayerStats
    SET
      TotalGames  = TotalGames + 1,
      Losses      = Losses + 1,
      AvgAccuracy = CASE 
                      WHEN TotalGames + 1 > 0 
                        THEN Wins / (TotalGames + 1) * 100 
                      ELSE 0 
                    END
    WHERE UserID = 
      CASE
        WHEN NEW.Player1ID = NEW.WinnerID THEN NEW.Player2ID
        ELSE NEW.Player1ID
      END;
    -- Weekly leaderboard update
    IF EXISTS (
      SELECT 1 FROM LeaderboardScores
      WHERE UserID = NEW.WinnerID AND Period = 'weekly' AND PeriodStart = wkStart
    ) THEN
      UPDATE LeaderboardScores
      SET Score = Score + 1, UpdatedAt = CURRENT_TIMESTAMP
      WHERE UserID = NEW.WinnerID AND Period = 'weekly' AND PeriodStart = wkStart;
    ELSE
      INSERT INTO LeaderboardScores
        (UserID, Score, LeaderboardRank, Period, PeriodStart, PeriodEnd)
      VALUES
        (NEW.WinnerID, 1, NULL, 'weekly', wkStart, wkEnd);
    END IF;

    -- Monthly leaderboard update
    IF EXISTS (
      SELECT 1 FROM LeaderboardScores
      WHERE UserID = NEW.WinnerID AND Period = 'monthly' AND PeriodStart = moStart
    ) THEN
      UPDATE LeaderboardScores
      SET Score = Score + 1, UpdatedAt = CURRENT_TIMESTAMP
      WHERE UserID = NEW.WinnerID AND Period = 'monthly' AND PeriodStart = moStart;
    ELSE
      INSERT INTO LeaderboardScores
        (UserID, Score, LeaderboardRank, Period, PeriodStart, PeriodEnd)
      VALUES
        (NEW.WinnerID, 1, NULL, 'monthly', moStart, moEnd);
    END IF;

    -- All-time leaderboard update
    INSERT INTO LeaderboardScores
      (UserID, Score, LeaderboardRank, Period, PeriodStart, PeriodEnd)
    VALUES
      (NEW.WinnerID, 1, NULL, 'alltime', '1970-01-01', '9999-12-31')
    ON DUPLICATE KEY UPDATE
      Score = Score + 1, UpdatedAt = CURRENT_TIMESTAMP;

  END IF;
END$$

DELIMITER ;





DELIMITER //

CREATE TRIGGER after_user_insert
AFTER INSERT ON Users
FOR EACH ROW
BEGIN
    INSERT INTO PlayerStats (UserID)
    VALUES (NEW.UserID);
END;
//

DELIMITER ;



DELIMITER //

CREATE TRIGGER after_user_promoted_to_admin
AFTER UPDATE ON Users
FOR EACH ROW
BEGIN
    -- Check if the role changed to 'admin'
    IF NEW.Role = 'admin' AND OLD.Role <> 'admin' THEN
        -- Insert admin permissions only if not already present
        IF NOT EXISTS (SELECT 1 FROM AdminRoles WHERE AdminID = NEW.UserID) THEN
            INSERT INTO AdminRoles (
                AdminID
            )
            VALUES (
                NEW.UserID,
            );
        END IF;
    END IF;
END;
//

DELIMITER ;
