#[derive(Debug)]
pub struct Card {
    name: String,
}

impl Card {
    pub fn new(name: &str) -> Self {
        Self {
           name: name.to_string(),
        }
    }
}

pub trait Drafter {
    fn pick(&self, pack: &Vec<Card>, owned_cards: &Vec<Card>) -> u32;
}
