CREATE INDEX idx_question_category ON Questions(CategoryID); 
CREATE INDEX idx_match_players ON Matches(Player1ID, Player2ID);
CREATE INDEX idx_round_match ON Rounds(MatchID); 
