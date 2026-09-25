package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"math/rand"
	"os"
	"strconv"
	"sync"
	"time"
)

type MacroParams struct {
	S0               float64 `json:"s0"`
	SigmaCrude       float64 `json:"sigma_crude"`
	JumpLambda       float64 `json:"jump_lambda"`
	JumpMu           float64 `json:"jump_mu"`
	CrackGas0        float64 `json:"crack_gas_0"`
	CrackDiesel0     float64 `json:"crack_diesel_0"`
	SigmaCrackGas    float64 `json:"sigma_crack_gas"`
	SigmaCrackDiesel float64 `json:"sigma_crack_diesel"`
	DayOfYear        int     `json:"day_of_year"`
	Freight0         float64 `json:"freight_0"`
	ChokepointLambda float64 `json:"chokepoint_lambda"`
	ChokepointJumpMu float64 `json:"chokepoint_jump_mu"`
	SprTrigger       float64 `json:"spr_trigger_price"`
	SprFloor         float64 `json:"spr_floor_price"`
	SprMaxDraw       float64 `json:"spr_max_draw_mbpd"`
	SaudiProd        float64 `json:"saudi_prod"`
	SaudiCap         float64 `json:"saudi_cap"`
	RussiaProd       float64 `json:"russia_prod"`
	RussiaDecay      float64 `json:"russia_decay"`
}

const (
	Days  = 180
	Sims  = 10000
	Dt    = 1.0 / 365.0
	TaxG  = 0.57
	DistG = 0.65
	TaxD  = 0.65
	DistD = 0.85
)

func main() {
	rand.Seed(time.Now().UnixNano())

	macroFile, err := os.Open("params_macro.json")
	if err != nil {
		legacyFile, legacyErr := os.Open("params.json")
		if legacyErr != nil {
			log.Fatalf("failed to open params_macro.json or params.json: %v / %v", err, legacyErr)
		}
		defer legacyFile.Close()
		var legacy MacroParams
		if err := json.NewDecoder(legacyFile).Decode(&legacy); err != nil {
			log.Fatalf("failed to decode legacy params.json: %v", err)
		}
		legacyDay := time.Now().Day()
		legacy.DayOfYear = legacyDay
		runSimulation(legacy)
		return
	}
	defer macroFile.Close()

	var p MacroParams
	if err := json.NewDecoder(macroFile).Decode(&p); err != nil {
		log.Fatalf("failed to decode params_macro.json: %v", err)
	}
	if p.DayOfYear == 0 {
		p.DayOfYear = time.Now().YearDay()
	}

	runSimulation(p)
}

func runSimulation(p MacroParams) {
	var wg sync.WaitGroup
	gasResults := make([][]string, Sims)
	dieselResults := make([][]string, Sims)

	fmt.Println("Running 10,000 multi-factor macro paths...")
	for i := 0; i < Sims; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			st := p.S0
			cGas := p.CrackGas0
			cDies := p.CrackDiesel0
			freight := p.Freight0
			saudiQ := p.SaudiProd
			russiaQ := p.RussiaProd

			gasPath := make([]string, Days)
			dieselPath := make([]string, Days)

			for t := 0; t < Days; t++ {
				russiaQ -= russiaQ * p.RussiaDecay * Dt
				saudiQ += 0.05 * (80.0 - st) * Dt
				if saudiQ > p.SaudiCap {
					saudiQ = p.SaudiCap
				}
				if saudiQ < 7.0 {
					saudiQ = 7.0
				}

				sprFlow := 0.0
				if st > p.SprTrigger {
					sprFlow = p.SprMaxDraw
				} else if st < p.SprFloor {
					sprFlow = -0.1
				}

				freightJump := 0.0
				if rand.Float64() < (p.ChokepointLambda * Dt) {
					freightJump = math.Abs(rand.NormFloat64()*2.0 + p.ChokepointJumpMu)
				}
				freight += 5.0*(p.Freight0-freight)*Dt + freightJump

				currentDay := float64((p.DayOfYear + t) % 365)
				seasonalGas := 5.0 * math.Sin((2.0*math.Pi/365.0)*currentDay-1.5)
				seasonalDiesel := 3.0 * math.Sin((2.0*math.Pi/365.0)*currentDay+0.8)
				cGas += seasonalGas*Dt + rand.NormFloat64()*1.2
				cDies += seasonalDiesel*Dt + rand.NormFloat64()*1.0

				supplyImbalance := (saudiQ + russiaQ + sprFlow) - (p.SaudiProd + p.RussiaProd)
				mu := -0.1 * supplyImbalance
				dS := mu*st*Dt + p.SigmaCrude*st*math.Sqrt(Dt)*rand.NormFloat64()
				st += dS
				st = math.Max(st, 0.01)

				gasPrice := (st / 42.0) + (cGas / 42.0) + (freight / 42.0) + TaxG + DistG
				dieselPrice := (st / 42.0) + (cDies / 42.0) + (freight / 42.0) + TaxD + DistD
				gasPath[t] = strconv.FormatFloat(gasPrice, 'f', 2, 64)
				dieselPath[t] = strconv.FormatFloat(dieselPrice, 'f', 2, 64)
			}

			gasResults[idx] = gasPath
			dieselResults[idx] = dieselPath
		}(i)
	}
	wg.Wait()

	if err := writeCSV("results_macro_gas.csv", gasResults); err != nil {
		log.Fatalf("failed to write macro gas results: %v", err)
	}
	if err := writeCSV("results_macro_diesel.csv", dieselResults); err != nil {
		log.Fatalf("failed to write macro diesel results: %v", err)
	}
	if err := writeCSV("results_gas.csv", gasResults); err != nil {
		log.Fatalf("failed to write gas results: %v", err)
	}
	if err := writeCSV("results_diesel.csv", dieselResults); err != nil {
		log.Fatalf("failed to write diesel results: %v", err)
	}
	fmt.Println("Simulation complete. Output saved to macro and legacy CSVs.")
}

func writeCSV(filename string, data [][]string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	writer.WriteAll(data)
	return writer.Error()
}
