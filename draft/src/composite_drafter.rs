use crate::api::*;
use std::collections::HashMap;
use std::collections::Vec;
pub struct CompositeDrafter {

}

// Draft brains will make determinations on how to draft based
// on various metrics provided to them within card data.

/* A rudimentary brain that counts mana symbols in mana costs and attempts to find cards
 with average color similar to that of the existing cards in our deck. */
pub struct DraftColorBrain {
}

impl DraftColorBrain {
    // Function that builds a hash map of colors and their weights; higher weights are closer to our
    // current colors.
    // TODO: In the python conversion, this state should be kept and updated incrementally, rather
    // than recalculated wholesale every pick.
    fn calc_preferences(&self, cards_owned: &[Card]) -> HashMap<BasicMana, i32> {
        let mut mana_prefs: HashMap<BasicMana, i32> = HashMap::new();
        for i in range(0, cards_owned.len()) {
            for symbol in range(0, i.mana_cost.len()) {
                // TODO: Find a good way to return the primitive mana types of complex mana types
                // and increment our hashmap values accordingly.
                match i.mana_cost[symbol] {
                    Mana::XCost(string) => (),
                    Mana::Phyrexian(basic) => mana_prefs.entry(basic).and_modify(|m| { m + 1 }).or_insert(1),
                    Mana::Split(basic, basic2) => {
                        mana_prefs.entry(basic).and_modify(|m| { m + 1 }.or_insert(1));
                        mana_prefs.entry(basic2).and_modify(|m| { m + 1 }.or_insert(1))
                    },
                    Mana::Standard(basic) => mana_prefs.entry(basic).and_modify(|m| { m + 2 }).or_insert(2),
                    Mana::NumGeneric(amt) => (),
                    Mana::SplitGeneric(basic) => mana_prefs.entry(basic).and_modify(|m| { m + 1 }).or_insert(1),
                }
            }
        }
        mana_prefs
    }

    // In truth I think this strategy is terrible and will move to clustering for python,
    // but I'm going to write it out as a way to help think through the problem.
    fn get_pack_weights<'a>(&self, pack: &'a [Card], cards_owned: &[Card],
                            draft_info: &DraftInfo) -> &'a [card_weight] {
        let prefs = calc_preferences;
        let mut weights: Vec<CardWeight> = Vec::new();
        for i in range(0, cards_owned.len()) {
            weights.push(get_card_weight(&self, pack[i], cards_owned, draft_info));
        };
        weights;
    }
    fn get_card_weight<'a>(&self, card: &'a Card, cards_owned: &[Card],
                           draft_info: &DraftInfo) -> (CardWeight){
        for symbol in range(0, card.mana_cost.len()) {
            // The mana cost structure sort of breaks down here. In c# I could do this much easier
            // with a lambda, not sure what the right solution is in rust. This match function could
            // also probably be merged with the one used for preference generation as well.
            match card.mana_cost[symbol] {
                Mana::XCost(string) => (),
                Mana::Phyrexian(basic) => match prefs.get(basic) {
                    some(val) => weight += val,
                    none => ()
                },
                Mana::Split(basic, basic2) => {
                    match prefs.get(basic) {
                        some(val) => weight += val / 2,
                        none => ()
                    };
                    match prefs.get(basic2) {
                        some(val) => weight += val / 2,
                        none => ()
                    }
                },
                Mana::Standard(basic) => match prefs.get(basic) {
                    some(val) => weight += val,
                    none => ()
                },
                Mana::NumGeneric(amt) => (),
                Mana::SplitGeneric(basic) => match prefs.get(basic) {
                    some(val) => weight += val,
                    none => ()
                },
            }
        }
        CardWeight {card: cards_owned[i], weight: weight}
    }
}

pub struct CardWeight {
    pub card: Card,
    pub weight: i32
}

pub trait DraftBrain {
    fn get_pack_weights<'a>(&self, pack: &'a [Card], cards_owned: &[Card],
                            draft_info: &DraftInfo) -> &'a Vec<CardWeight>{
        let mut prefernces: Vec<card_weight> = Vec::new();
        for i in range(0, pack.len()){
            preferences.push(get_card_weight(&self, pack[a], cards_owned, draft_info))
        };
        preferences
    }
    fn get_card_weight<'a>(&self, card: &'a Card, cards_owned: &[Card],
                            draft_info: &DraftInfo) -> (CardWeight);
}
