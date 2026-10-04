--
-- PostgreSQL database dump
--

\restrict Gri6yv3NEHVU1hg34FmJjgfmZki60ytxgXJ9gS1jOeeLURB4D6GSCI2J0UtOCkW

-- Dumped from database version 17.7
-- Dumped by pg_dump version 17.7

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: get_account_turnover(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_account_turnover(p_account_id integer, p_year integer) RETURNS TABLE(month_num integer, charges numeric, payments numeric, deviation numeric, saldo_end numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        EXTRACT(MONTH FROM s.period)::INT,
        COALESCE(c.amount, 0),
        COALESCE(p.amount, 0),
        COALESCE(c.amount, 0) - COALESCE(p.amount, 0) AS deviation,
        s.saldo_end
    FROM saldo s
    LEFT JOIN charges c ON c.account_id = s.account_id AND c.period = s.period
    LEFT JOIN payments p ON p.account_id = s.account_id AND p.period = s.period
    WHERE s.account_id = p_account_id
      AND EXTRACT(YEAR FROM s.period) = p_year
    ORDER BY 1;
END;
$$;


ALTER FUNCTION public.get_account_turnover(p_account_id integer, p_year integer) OWNER TO postgres;

--
-- Name: get_debtors_summary(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_debtors_summary(p_period date) RETURNS TABLE(account_id integer, last_charge numeric, saldo numeric, debt_1_month numeric, debt_2_months numeric, debt_3_months numeric, debt_over_3 numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    WITH last_data AS (
        SELECT
            s.account_id,
            COALESCE(c.amount, 0) AS last_charge,
            s.saldo_end AS saldo,
            s.period
        FROM saldo s
        LEFT JOIN charges c ON c.account_id = s.account_id AND c.period = s.period
        WHERE s.period = p_period
    )
    SELECT
        ld.account_id,
        ld.last_charge,
        ld.saldo,
        CASE WHEN ld.saldo > 0 AND ld.saldo <= ld.last_charge
             THEN ld.saldo ELSE 0 END AS debt_1_month,
        CASE WHEN ld.saldo > ld.last_charge AND ld.saldo <= 2 * ld.last_charge
             THEN ld.saldo ELSE 0 END AS debt_2_months,
        CASE WHEN ld.saldo > 2 * ld.last_charge AND ld.saldo <= 3 * ld.last_charge
             THEN ld.saldo ELSE 0 END AS debt_3_months,
        CASE WHEN ld.saldo > 3 * ld.last_charge
             THEN ld.saldo ELSE 0 END AS debt_over_3
    FROM last_data ld
    WHERE ld.saldo > 0
    ORDER BY ld.account_id;
END;
$$;


ALTER FUNCTION public.get_debtors_summary(p_period date) OWNER TO postgres;

--
-- Name: get_turnover_sheet(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_turnover_sheet(p_year integer) RETURNS TABLE(account_id integer, month_num integer, charges numeric, payments numeric, saldo_end numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.account_id,
        EXTRACT(MONTH FROM s.period)::INT AS month_num,
        COALESCE(c.amount, 0) AS charges,
        COALESCE(p.amount, 0) AS payments,
        s.saldo_end
    FROM saldo s
    LEFT JOIN charges c ON c.account_id = s.account_id AND c.period = s.period
    LEFT JOIN payments p ON p.account_id = s.account_id AND p.period = s.period
    WHERE EXTRACT(YEAR FROM s.period) = p_year
    ORDER BY s.account_id, month_num;
END;
$$;


ALTER FUNCTION public.get_turnover_sheet(p_year integer) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: charges; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.charges (
    id integer NOT NULL,
    account_id integer NOT NULL,
    period date NOT NULL,
    amount numeric(12,2) NOT NULL,
    service_type character varying(100) DEFAULT 'Коммунальные'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.charges OWNER TO postgres;

--
-- Name: charges_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.charges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.charges_id_seq OWNER TO postgres;

--
-- Name: charges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.charges_id_seq OWNED BY public.charges.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    account_id integer NOT NULL,
    period date NOT NULL,
    amount numeric(12,2) NOT NULL,
    pay_date date NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.payments OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_id_seq OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: saldo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.saldo (
    id integer NOT NULL,
    account_id integer NOT NULL,
    period date NOT NULL,
    saldo_begin numeric(12,2) DEFAULT 0,
    saldo_end numeric(12,2) DEFAULT 0
);


ALTER TABLE public.saldo OWNER TO postgres;

--
-- Name: saldo_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.saldo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.saldo_id_seq OWNER TO postgres;

--
-- Name: saldo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.saldo_id_seq OWNED BY public.saldo.id;


--
-- Name: charges id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.charges ALTER COLUMN id SET DEFAULT nextval('public.charges_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: saldo id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saldo ALTER COLUMN id SET DEFAULT nextval('public.saldo_id_seq'::regclass);


--
-- Data for Name: charges; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.charges (id, account_id, period, amount, service_type, created_at) FROM stdin;
1	1	2024-01-01	4590.22	Коммунальные	2026-09-28 18:28:02.810133
2	1	2024-02-01	4589.64	Коммунальные	2026-09-28 18:28:02.867761
3	2	2024-01-01	4870.26	Коммунальные	2026-09-28 18:28:02.897233
16	2	2024-12-01	1000.00	Тест	2026-09-28 18:43:28.768886
6	1	2024-03-01	5030.62	Коммунальные	2026-09-28 18:32:17.802773
7	1	2024-04-01	4502.41	Коммунальные	2026-09-28 18:32:17.802773
8	1	2024-05-01	4455.16	Коммунальные	2026-09-28 18:32:17.802773
9	1	2024-06-01	4030.90	Коммунальные	2026-09-28 18:32:17.802773
10	1	2024-07-01	4528.61	Коммунальные	2026-09-28 18:32:17.802773
11	1	2024-08-01	4579.44	Коммунальные	2026-09-28 18:32:17.802773
12	1	2024-09-01	4851.68	Коммунальные	2026-09-28 18:32:17.802773
13	1	2024-10-01	4823.83	Коммунальные	2026-09-28 18:32:17.802773
14	1	2024-11-01	0.00	Коммунальные	2026-09-28 18:32:17.802773
15	1	2024-12-01	0.00	Коммунальные	2026-09-28 18:32:17.802773
18	5	2024-12-01	1234.56	Тест	2026-10-04 13:20:03.036332
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payments (id, account_id, period, amount, pay_date, created_at) FROM stdin;
1	1	2024-01-01	4004.06	2024-01-15	2026-09-28 18:28:02.83941
2	1	2024-02-01	4004.06	2024-02-15	2026-09-28 18:28:02.876393
3	2	2024-01-01	0.00	2024-01-15	2026-09-28 18:28:02.905895
6	1	2024-03-01	586.16	2024-03-15	2026-09-28 18:32:17.84314
7	1	2024-04-01	6127.10	2024-04-15	2026-09-28 18:32:17.84314
8	1	2024-05-01	6405.16	2024-05-15	2026-09-28 18:32:17.84314
9	1	2024-06-01	4405.16	2024-06-15	2026-09-28 18:32:17.84314
10	1	2024-07-01	4030.90	2024-07-15	2026-09-28 18:32:17.84314
11	1	2024-08-01	4528.61	2024-08-15	2026-09-28 18:32:17.84314
12	1	2024-09-01	4579.44	2024-09-15	2026-09-28 18:32:17.84314
13	1	2024-10-01	4851.68	2024-10-15	2026-09-28 18:32:17.84314
14	1	2024-11-01	0.00	2024-11-15	2026-09-28 18:32:17.84314
15	1	2024-12-01	0.00	2024-12-15	2026-09-28 18:32:17.84314
16	5	2024-12-01	500.00	2024-12-15	2026-10-04 13:20:57.991188
\.


--
-- Data for Name: saldo; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.saldo (id, account_id, period, saldo_begin, saldo_end) FROM stdin;
3	2	2024-01-01	14476.86	19347.12
1	1	2024-01-01	5379.37	5965.53
2	1	2024-02-01	5965.53	6551.11
7	1	2024-03-01	6551.11	10995.57
8	1	2024-04-01	10995.57	9092.63
9	1	2024-05-01	9092.63	10370.69
10	1	2024-06-01	10370.69	9996.43
11	1	2024-07-01	9996.43	10494.14
12	1	2024-08-01	10494.14	10544.97
13	1	2024-09-01	10544.97	10817.21
14	1	2024-10-01	10817.21	10789.36
15	1	2024-11-01	10789.36	10789.36
16	1	2024-12-01	10789.36	10789.36
17	5	2024-12-01	0.00	734.56
\.


--
-- Name: charges_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.charges_id_seq', 18, true);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payments_id_seq', 16, true);


--
-- Name: saldo_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.saldo_id_seq', 17, true);


--
-- Name: charges charges_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.charges
    ADD CONSTRAINT charges_pkey PRIMARY KEY (id);


--
-- Name: charges charges_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.charges
    ADD CONSTRAINT charges_unique UNIQUE (account_id, period);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: payments payments_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_unique UNIQUE (account_id, period);


--
-- Name: saldo saldo_account_id_period_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saldo
    ADD CONSTRAINT saldo_account_id_period_key UNIQUE (account_id, period);


--
-- Name: saldo saldo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saldo
    ADD CONSTRAINT saldo_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict Gri6yv3NEHVU1hg34FmJjgfmZki60ytxgXJ9gS1jOeeLURB4D6GSCI2J0UtOCkW

