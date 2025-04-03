use crate::{Board, Piece, Row};
use crate::lock_data::LockResult;
use crate::evaluate::Standard;

pub struct ScoredBoard<R: Row> {
    pub board: Board<R>,
    pub lock: LockResult,
    pub score: i32,
}

pub fn choose_best_board<R: Row>(
    boards: Vec<(Board<R>, LockResult, u32, Piece)>,
    config: &Standard,
) -> Option<ScoredBoard<R>> {
    boards
        .into_iter()
        .map(|(board, lock, move_time, placed)| {
            let (transient, reward) = config.evaluate_board(&board, &lock, move_time, placed);
            let score = transient + reward;
            ScoredBoard { board, lock, score }
        })
        .max_by_key(|sb| sb.score)
}
