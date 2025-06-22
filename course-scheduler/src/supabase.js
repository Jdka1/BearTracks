// src/supabase.js
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = "https://mugwxxnxccvladdohfsq.supabase.co"; // replace with your URL
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im11Z3d4eG54Y2N2bGFkZG9oZnNxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA1NDk0NDMsImV4cCI6MjA2NjEyNTQ0M30.icsCx7DXzSL5my5pwmY_rS7ZTUyH7aN1OeV9y4mh6Cw"; // replace with anon key from project settings

export const supabase = createClient(supabaseUrl, supabaseKey);
